import json
import os
import random

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models as django_models
from django.db.models import Avg
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from movies.models import Movie
from utils.get_image import get_image
from utils.recommender import recommend
from user.models import UserProfile, MovieWatchRecord, MovieRating, RecEvent
from utils.recommender.recommend import Recommender


class DetailView(LoginRequiredMixin, View):
    def get(self, request, movie_id):
        movie = Movie.objects.get(movie_id=movie_id)
        movie_model = {
            'id': movie.movie_id,
            'title': movie.title,
            'year': movie.year,
            'genre': movie.genres,
            'rating': movie.avg_rating,
            'poster_url': get_image.get_image_url(movie.movie_id, use_thumbnail=False),
            'description': '近未来的地球黄沙遍野，小麦、秋葵等基础农作物相继因枯萎病灭绝，人类不再像从前那样仰望星空，放纵想象力和灵感的迸发，而是每日在沙尘暴的肆虐下倒数着所剩不多的光景。在家务农的前NASA宇航员库珀接连在女儿墨菲的房间发现了奇异磁场，在神秘力量的指引下，他和一众伙伴踏上了穿越星际的旅程，寻找人类新的家园。'
        }

        # Feature 2: 使用相似电影推荐替代热门推荐
        similar_movies, source_title = Recommender.get_similar_movies(movie_id, top_k=5)

        if similar_movies:
            rec_section_title = f"和《{source_title or movie.title}》相似的影片"
        else:
            # 降级为热门推荐
            similar_movies = Recommender.get_hot_movies(5)
            rec_section_title = "热门推荐"

        recommendations = []
        for mmovie in similar_movies:
            recommendations.append({
                'id': mmovie.movie_id,
                'title': mmovie.title,
                'genre': mmovie.genres,
                'rating': mmovie.avg_rating,
                'poster_url': get_image.get_image_url(mmovie.movie_id, use_thumbnail=True),
            })

        context = {
            'movie': movie_model,
            'recommendations': recommendations,
            'rec_section_title': rec_section_title,
        }

        # Feature 5: 记录展示事件（A/B 实验）
        try:
            profile = UserProfile.objects.get(user=request.user)
            rec_group = getattr(profile, 'rec_group', 'A')
            RecEvent.objects.create(
                user=request.user,
                movie_id=movie_id,
                event_type='impression',
                rec_group=rec_group,
                source='detail_rec',
            )
        except Exception:
            pass

        # 将行为数据保存到redis中
        recommend.Recommender.record_user_action(request.user, movie_id, 'click')

        # Feature 4: 增量更新用户向量
        Recommender.update_user_vector(request.user.id, movie_id, weight=0.3)

        userprofile = UserProfile.objects.filter(user=request.user)[0]
        userprofile.point_count += 1  # 点击数加一
        MovieWatchRecord.objects.update_or_create(
            user=request.user,
            movie_id=movie_id,
            defaults={},
        )

        # Feature 5: 记录点击事件（A/B 实验）
        try:
            RecEvent.objects.create(
                user=request.user,
                movie_id=movie_id,
                event_type='click',
                rec_group=rec_group,
                source='detail_rec',
            )
        except Exception:
            pass

        print(f"{userprofile}用户共点击了{userprofile.point_count}次")
        userprofile.clicked_movie_ids.append(movie_id)  # 点击电影加入到电影队列
        userprofile.save()

        return render(request, 'detaill.html', context=context)


class CollectionView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            movie_id = data.get('movie_id')
            print(f"后端接收到收藏请求,用户{request.user}本次收藏电影编号{movie_id}")
            if not movie_id:
                print("movies_id为空,收藏失败")
                return JsonResponse({'status': 'error', 'message': '缺少 movie_id 参数'}, status=400)

            # 收藏的电影存储到 Redis
            recommend.Recommender.record_user_action(request.user, movie_id, 'collect')

            # 同时将数据同步到数据库
            userprofile = UserProfile.objects.filter(user=request.user)[0]
            userprofile.collected_movie_ids.append(movie_id)
            userprofile.save()

            # Feature 4: 增量更新用户向量（收藏权重更高）
            Recommender.update_user_vector(request.user.id, movie_id, weight=0.7)

            # Feature 5: 记录收藏事件（A/B 实验）
            try:
                profile = UserProfile.objects.get(user=request.user)
                rec_group = getattr(profile, 'rec_group', 'A')
                RecEvent.objects.create(
                    user=request.user,
                    movie_id=movie_id,
                    event_type='collect',
                    rec_group=rec_group,
                    source='detail_rec',
                )
            except Exception:
                pass

            return JsonResponse({'status': 'success', 'message': '收藏成功！'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '请求体格式错误'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class RateMovieView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)

            movie_id = int(data.get("movie_id"))
            rating = int(data.get("rating"))

            if rating < 1 or rating > 5:
                return JsonResponse({
                    "status": "error",
                    "message": "评分必须在 1~5 之间"
                })

            obj, created = MovieRating.objects.get_or_create(
                user=request.user,
                movie_id=movie_id,
                defaults={"rating": rating}
            )

            if not created:
                obj.rating = rating
                obj.save()

            avg_rating = MovieRating.objects.filter(
                movie_id=movie_id
            ).aggregate(avg=Avg("rating"))["avg"]

            # Feature 4: 增量更新用户向量（评分权重最高）
            Recommender.update_user_vector(request.user.id, movie_id, weight=1.0)

            # 同时记录到 Redis
            recommend.Recommender.record_user_action(request.user, movie_id, 'rating')

            # Feature 5: 记录评分事件（A/B 实验）
            try:
                profile = UserProfile.objects.get(user=request.user)
                rec_group = getattr(profile, 'rec_group', 'A')
                RecEvent.objects.create(
                    user=request.user,
                    movie_id=movie_id,
                    event_type='rating',
                    rec_group=rec_group,
                    source='detail_rec',
                )
            except Exception:
                pass

            return JsonResponse({
                "status": "success",
                "movie_id": movie_id,
                "new_rating": round(avg_rating, 2) if avg_rating else rating
            })

        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            })
