
import json
import random
import os
import time
from datetime import datetime

import django
from django.db.models import Q, Case, When
from django.shortcuts import redirect, render

from MoviesRec import settings
from movies.models import Movie
from ratings.models import Rating
from user.models import UserProfile
from utils.get_image import get_image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MoviesRec.settings')

from django_redis import get_redis_connection
import torch
import numpy as np



class Recommender:
    _MODEL = None
    _ITEM_EMBS = None
    _ITEM_MAP = None
    _REV_ITEM_MAP = None
    _EMB_VERSION = 1

    @staticmethod
    def load_model():
        if Recommender._ITEM_EMBS is None:
            BASE_DIR = os.path.dirname(os.path.abspath(__file__))
            MODEL_PATH = os.path.join(BASE_DIR, "ncf_production.pth")

            checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)

            Recommender._ITEM_EMBS = checkpoint["item_embs"]
            Recommender._ITEM_MAP = checkpoint["item_map"]
            Recommender._REV_ITEM_MAP = {v: k for k, v in Recommender._ITEM_MAP.items()}

    @staticmethod
    def get_redis_conn():
        return get_redis_connection("history")

    @staticmethod
    def record_user_action(user_id, movie_id, action_type):
        conn = Recommender.get_redis_conn()

        key = f"user_history:{user_id}"
        data = json.dumps({
            "mid": int(movie_id),
            "type": action_type,
            "ts": datetime.now().timestamp()
        })

        conn.lpush(key, data)
        print(f"成功记录用户行为：{user_id} {movie_id} {action_type}")
        conn.ltrim(key, 0, 99)

    # ==================== Feature 4: 用户向量增量更新 ====================
    @staticmethod
    def update_user_vector(user_id, movie_id, weight):
        Recommender.load_model()
        ITEM_EMBS = Recommender._ITEM_EMBS
        ITEM_MAP = Recommender._ITEM_MAP
        conn = Recommender.get_redis_conn()

        if movie_id not in ITEM_MAP:
            return

        idx = ITEM_MAP[movie_id]
        movie_emb = ITEM_EMBS[idx]

        vec_key = f"user_vec:{user_id}"
        time_key = f"user_vec_time:{user_id}"
        version_key = f"user_vec_version:{user_id}"

        stored_version = conn.get(version_key)
        if stored_version and int(stored_version) != Recommender._EMB_VERSION:
            conn.delete(vec_key, time_key)

        now = time.time()
        old_vec_raw = conn.get(vec_key)
        old_time_raw = conn.get(time_key)

        if old_vec_raw and old_time_raw:
            old_vec = np.frombuffer(old_vec_raw, dtype=np.float32)
            old_time = float(old_time_raw)
            dt = now - old_time
            gamma = np.exp(-0.01 * dt)
            new_vec = old_vec * gamma + movie_emb * weight
        else:
            new_vec = movie_emb * weight

        conn.set(vec_key, new_vec.astype(np.float32).tobytes())
        conn.set(time_key, str(now))
        conn.set(version_key, Recommender._EMB_VERSION)

    @staticmethod
    def get_ncf_recommendations(user_id, top_k=10):
        Recommender.load_model()
        ITEM_EMBS = Recommender._ITEM_EMBS
        ITEM_MAP = Recommender._ITEM_MAP
        REV_ITEM_MAP = Recommender._REV_ITEM_MAP
        conn = Recommender.get_redis_conn()

        user_vec = None
        vec_key = f"user_vec:{user_id}"
        version_key = f"user_vec_version:{user_id}"
        stored_version = conn.get(version_key)
        if stored_version and int(stored_version) == Recommender._EMB_VERSION:
            cached_vec = conn.get(vec_key)
            if cached_vec:
                user_vec = np.frombuffer(cached_vec, dtype=np.float32)

        redis_actions = conn.lrange(f"user_history:{user_id}", 0, -1)
        actions_list = []
        if redis_actions:
            actions_list = [json.loads(a) for a in redis_actions]
        else:
            try:
                profile = UserProfile.objects.get(user_id=user_id)

                def parse_ids(data):
                    if isinstance(data, list):
                        return data
                    try:
                        return json.loads(data) if data else []
                    except:
                        return []

                clicked_ids = parse_ids(profile.clicked_movie_ids)
                collected_ids = parse_ids(profile.collected_movie_ids)

                actions_list += [{'mid': int(i), 'type': 'click'} for i in clicked_ids]
                actions_list += [{'mid': int(i), 'type': 'collect'} for i in collected_ids]

            except UserProfile.DoesNotExist:
                pass

        if not actions_list:
            hot_movies = Movie.objects.order_by('-avg_rating')[:top_k]
            return list(hot_movies), None

        now = time.time()
        best_source = None
        best_source_weight = -1

        if user_vec is None:
            user_vec = np.zeros(ITEM_EMBS.shape[1])
            total_weight = 0

            for action in actions_list:
                m_id = action['mid']
                if m_id not in ITEM_MAP:
                    continue

                idx = ITEM_MAP[m_id]

                action_type = action.get("type", "click")
                base_weight = {
                    "click": 0.3,
                    "collect": 0.7,
                    "rating": 1.0
                }.get(action_type, 0.3)

                ts = action.get("ts", now)
                decay = np.exp(-0.01 * (now - ts))

                weight = base_weight * decay

                user_vec += ITEM_EMBS[idx] * weight
                total_weight += weight

                if weight > best_source_weight:
                    best_source_weight = weight
                    best_source = m_id

            if total_weight > 0:
                user_vec /= total_weight
                conn.set(vec_key, user_vec.astype(np.float32).tobytes())
                conn.set(f"user_vec_time:{user_id}", str(now))
                conn.set(version_key, Recommender._EMB_VERSION)
            else:
                return list(Movie.objects.order_by('-avg_rating')[:top_k]), None
        else:
            for action in actions_list:
                ts = action.get("ts", now)
                decay = np.exp(-0.01 * (now - ts))
                base_weight = {
                    "click": 0.3,
                    "collect": 0.7,
                    "rating": 1.0
                }.get(action.get("type", "click"), 0.3)
                weight = base_weight * decay
                if weight > best_source_weight:
                    best_source_weight = weight
                    best_source = action['mid']

        source_title = None
        if best_source:
            try:
                source_title = Movie.objects.get(movie_id=best_source).title
            except Movie.DoesNotExist:
                pass

        norm_user = user_vec / (np.linalg.norm(user_vec) + 1e-9)
        norm_items = ITEM_EMBS / (np.linalg.norm(ITEM_EMBS, axis=1, keepdims=True) + 1e-9)

        scores = np.dot(norm_items, norm_user)

        top_indices = scores.argsort()[-top_k:][::-1]
        recommended_ids = [REV_ITEM_MAP[i] for i in top_indices]

        preserved_order = Case(*[
            When(movie_id=pk, then=pos)
            for pos, pk in enumerate(recommended_ids)
        ])

        movies = Movie.objects.filter(
            movie_id__in=recommended_ids
        ).order_by(preserved_order)

        return list(movies), source_title


    @staticmethod
    def get_preference_based_recommend(user_profile, top_n=10):
        preferred_genres = user_profile.preferred_genres
        content_query = Q()
        for genre in preferred_genres:
            content_query |= Q(genres__icontains=genre)

        content_candidates = Movie.objects.filter(content_query).order_by('-avg_rating')
        if user_profile.is_explore:
            rate = 0.5
        else:
            rate = 0.7
        content_count = int(top_n * rate)
        content_list = list(content_candidates[:content_count * 3])
        if len(content_list) >= content_count:
            content_recommendations = random.sample(content_list, content_count)
        else:
            content_recommendations = content_list

        exclude_query = Q()
        for genre in preferred_genres:
            exclude_query |= Q(genres__icontains=genre)

        other_candidates = Movie.objects.filter(~exclude_query).order_by('-avg_rating')

        other_count = top_n - content_count
        other_list = list(other_candidates[:other_count * 3])
        if len(other_list) >= other_count:
            other_recommendations = random.sample(other_list, other_count)
        else:
            other_recommendations = other_list

        final_recommendations = content_recommendations + other_recommendations
        random.shuffle(final_recommendations)
        return final_recommendations

    @staticmethod
    def get_hot_movies(top_n=10):
        from django.db.models import Count, Avg

        movies = (
            Rating.objects
            .values("movie_id")
            .annotate(
                avg_rating=Avg("rating"),
                count=Count("id")
            )
            .order_by("-count", "-avg_rating")[:top_n]
        )

        movie_ids = [m["movie_id"] for m in movies]
        return Movie.objects.filter(movie_id__in=movie_ids)

    @staticmethod
    def get_similar_movies(movie_id, top_k=5):
        Recommender.load_model()
        ITEM_EMBS = Recommender._ITEM_EMBS
        ITEM_MAP = Recommender._ITEM_MAP
        REV_ITEM_MAP = Recommender._REV_ITEM_MAP

        movie_id = int(movie_id)

        if movie_id not in ITEM_MAP:
            return [], None

        idx = ITEM_MAP[movie_id]
        target_emb = ITEM_EMBS[idx]

        norm_target = target_emb / (np.linalg.norm(target_emb) + 1e-9)
        norm_items = ITEM_EMBS / (np.linalg.norm(ITEM_EMBS, axis=1, keepdims=True) + 1e-9)

        scores = np.dot(norm_items, norm_target)

        top_indices = scores.argsort()[-(top_k + 1):][::-1]
        similar_movie_ids = []
        for i in top_indices:
            mid = REV_ITEM_MAP[i]
            if mid != movie_id:
                similar_movie_ids.append(mid)
            if len(similar_movie_ids) >= top_k:
                break

        preserved_order = Case(*[
            When(movie_id=pk, then=pos)
            for pos, pk in enumerate(similar_movie_ids)
        ])

        similar_movies = Movie.objects.filter(
            movie_id__in=similar_movie_ids
        ).order_by(preserved_order)

        try:
            source_title = Movie.objects.get(movie_id=movie_id).title
        except Movie.DoesNotExist:
            source_title = None

        return list(similar_movies), source_title

    @staticmethod
    def _fill_to_top_k(movies, top_k, reason, extra_exclude_ids=None):
        exclude_ids = {m['id'] for m in movies}
        if extra_exclude_ids:
            exclude_ids |= extra_exclude_ids

        if len(movies) < top_k:
            need = top_k - len(movies)
            fallback = Movie.objects.exclude(
                movie_id__in=exclude_ids
            ).order_by('-avg_rating')[:need * 3]
            fallback_list = list(fallback)
            random.shuffle(fallback_list)
            for m in fallback_list:
                if len(movies) >= top_k:
                    break
                if m.movie_id in exclude_ids:
                    continue
                exclude_ids.add(m.movie_id)
                movies.append({
                    "id": m.movie_id,
                    "title": m.title,
                    "genre": m.genres,
                    "rating": m.avg_rating,
                    "cover_url": get_image.get_image_url(m.movie_id, use_thumbnail=True),
                    "reason": reason or "大家都在看",
                })
        return movies[:top_k]

    @staticmethod
    def recommondMix(request, top_k=10):
        if request.user.is_authenticated:
             try:
                 user_pref = UserProfile.objects.get(user=request.user)
             except UserProfile.DoesNotExist:
                 return redirect("collect")

             rec_group = getattr(user_pref, 'rec_group', 'A')

             if user_pref.point_count < 30:
                 recommended_movies = Recommender.get_preference_based_recommend(user_pref, top_k)

                 genre_names = user_pref.preferred_genres[:2] if user_pref.preferred_genres else []
                 reason = f"因为你的喜好类型：{'、'.join(genre_names)}" if genre_names else "为你精心挑选"

                 recommended_movies = Recommender.append_images(recommended_movies, reason=reason)
                 return Recommender._fill_to_top_k(recommended_movies, top_k, reason)
             else:
                 recommended_movies, source_title = Recommender.get_ncf_recommendations(request.user, top_k)

                 if source_title:
                     reason = f"因为你喜欢《{source_title}》"
                 else:
                     reason = "基于你的观影偏好"

                 if rec_group == 'B' and recommended_movies:
                     split = max(1, int(len(recommended_movies) * 0.3))
                     if split > 0 and len(recommended_movies) > split:
                         existing_ids = {m.movie_id for m in recommended_movies}
                         diverse_candidates = list(Movie.objects.exclude(
                             movie_id__in=existing_ids
                         ).order_by('?')[:split])
                         recommended_movies = recommended_movies[:-split] + diverse_candidates

                 recommended_movies = Recommender.append_images(recommended_movies, reason=reason)
                 return Recommender._fill_to_top_k(recommended_movies, top_k, reason)
        else:
            recommended_movies = Recommender.get_hot_movies(top_k)
            reason = "大家都在看"
            recommended_movies = Recommender.append_images(recommended_movies, reason=reason)
            return Recommender._fill_to_top_k(recommended_movies, top_k, reason)

    @staticmethod
    def append_images(all_movies, reason=None):
        seen_ids = set()
        movies = []
        for movie in all_movies:
            mid = movie.movie_id
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            movies.append({
                "id": mid,
                "title": movie.title,
                "genre": movie.genres,
                "rating": movie.avg_rating,
                "cover_url": get_image.get_image_url(mid, use_thumbnail=True),
                "reason": reason or "大家都在看",
            })
        return movies
