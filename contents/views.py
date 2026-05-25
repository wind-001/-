import json
from collections import Counter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db.models import Count, Avg

from MoviesRec import settings
from movies.models import Movie
from user.models import UserProfile, MovieWatchRecord, User, MovieRating
from utils.genres import Genres
from utils.get_image import get_image
from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
from django.core.paginator import Paginator
from django.conf import settings
from utils.recommender import recommend
import os
import random

from utils.recommender.recommend import Recommender
from verification.emailCode.EmailSendMovies import MovieEmailSender


class IndexView(View):
    def get(self,request):
        if request.user.is_authenticated:
            context = {
                "movies": self.get_movie_data()[:5],
                # 轮播图 数据
                "carousel_slides": self.get_carousel_data(),
                # 实时推荐10部
                "realtime_movies": recommend.Recommender.recommondMix(request, 10),
                'point_counts': UserProfile.objects.get(user_id=request.user.id).point_count
            }
        else:
            context = {
                "movies": self.get_movie_data()[:5],
                # 轮播图 数据
                "carousel_slides": self.get_carousel_data(),
                # 主页推荐的前四部
                "realtime_movies": self.get_movie_data()[:10] , # 实时推荐取前10部
                'point_counts': -1,
            }
        return render(request, "index.html", context)
    # 主页<猜你喜欢>电影数据
    def get_movie_data(self,top_k=10):
        hot_movies = recommend.Recommender.get_hot_movies(top_k)
        movies = [
            {
                "id": movie.movie_id,
                "title": movie.title,
                "genre": movie.genres,
                "rating": movie.avg_rating,
                "cover_url": get_image.get_image_url(movie.movie_id, use_thumbnail=True),
                "reason": "大家都在看",
            }
            for movie in hot_movies
        ]
        return movies

    # 模拟轮播图数据
    def get_carousel_data(self):
        return [
            {
                "id": 1,
                "image_url": "/static/image/20532-Sansho the Bailiff.jpg",
                "title": "智能电影推荐系统",
                "description": "基于用户行为与深度学习算法，为你精准推荐心仪的影片"
            },
            {
                "id": 2,
                "image_url": "/static/image/686-Contact.jpg",
                "title": "实时更新推荐列表",
                "description": "根据你的观影记录、评分偏好动态调整推荐内容"
            },
            {
                "id": 3,
                "image_url": "/static/image/614-Wild Strawberries.jpg",
                "title": "海量影片库",
                "description": "覆盖科幻、悬疑、剧情、动作等全品类优质影片"
            }
        ]








class CategoryView(LoginRequiredMixin,View):
    def get(self, request):
        # 1. 获取前端传来的参数
        # 注意：genre 接收英文名用于数据库查询，因为数据库存的是英文
        genre = request.GET.get('genre', 'Action')
        sort_by = request.GET.get('sort', 'year')
        page_number = request.GET.get('page', 1)

        # 2. 数据库查询与排序
        movies_query = Movie.objects.filter(genres__contains=genre)

        if sort_by == 'rating':
            # 直接使用模型中的 avg_rating 字段排序，无需 annotate
            movies_query = movies_query.order_by('-avg_rating', '-year')
        else:
            movies_query = movies_query.order_by('-year')

        # 3. 分页处理 (每页15个)
        paginator = Paginator(movies_query, 15)
        page_obj = paginator.get_page(page_number)

        # 5. 构造电影 JSON 数据
        movies_list = []
        for mmovie in page_obj:
            raw_rating = getattr(mmovie, 'avg_rating', 0) or 0
            # 建议修改字段映射，确保 ID 始终一致
            movies_list.append({
                'id': str(mmovie.movie_id),  # 统一转为字符串，防止前端解析长整型溢出
                'title': mmovie.title,
                'year': mmovie.year,
                'rating': round(float(raw_rating), 1) if raw_rating else 0,
                'poster_url': get_image.get_image_url(mmovie.movie_id, use_thumbnail=True),
            })

        # 6. 处理 Ajax 请求 (点击左侧分类或分页时触发)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'movies': movies_list,
                'current_page': page_obj.number,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'total_pages': paginator.num_pages
            })

        # 7. 处理初次页面加载 (渲染题材列表)
        # 获取所有不重复的题材字符串
        raw_genres_list = Movie.objects.values_list('genres', flat=True).distinct()
        unique_genres_en = set()
        for item in raw_genres_list:
            if item:
                # 兼容逗号或竖线分隔
                parts = item.replace('|', ',').split(',')
                for p in parts:
                    if p.strip():
                        unique_genres_en.add(p.strip())

        # 构造带有中文翻译和选中状态的列表
        genre_list = []
        for en_name in sorted(list(unique_genres_en)):
            zh_name = Genres.GENRE_MAP.get(en_name, en_name)  # 获取中文翻译
            genre_list.append({
                'en': en_name,
                'zh': zh_name,
                'flag': 'True' if en_name == genre else 'False',  # 用于前端变红
            })

        context = {
            'genre_list': genre_list,
            'movies_list': movies_list,
            'genre': genre,
            'page_obj': page_obj,
        }
        return render(request, 'category.html', context=context)


class SearchView(LoginRequiredMixin,View):
    def get(self, request,movies_name):
        movies_query = Movie.objects.filter(title__icontains=movies_name)
        movies_list = []
        if movies_query:
            movies_list = [
                {
                    'id': movie.movie_id,
                    'title': movie.title,
                    'year': movie.year,
                    'rating': round(float(movie.avg_rating), 1) if movie.avg_rating else 0,
                    'poster_url': get_image.get_image_url(movie.movie_id, use_thumbnail=True),
                }
                for movie in movies_query
            ]
            #将搜索的电影加入到用户收藏队列中,同时将数据同步到数据库,搜索与收藏同权重
            userprofile = UserProfile.objects.filter(user=request.user)[0]
            rec_group = getattr(userprofile, 'rec_group', 'A')
            for movie in movies_list:
                movie_id = movie.get('id')
                recommend.Recommender.record_user_action(request.user, movie_id, 'collect')
            # 同时将数据同步到数据库
                userprofile.collected_movie_ids.append(movie_id)  # 收藏电影加入到电影队列
                # Feature 5: 记录搜索收藏事件
                try:
                    from user.models import RecEvent
                    RecEvent.objects.create(
                        user=request.user,
                        movie_id=movie_id,
                        event_type='collect',
                        rec_group=rec_group,
                        source='search',
                    )
                except Exception:
                    pass
                userprofile.save()
        return render(request, 'search.html', {'movies_list': movies_list})

class ProfileView(LoginRequiredMixin,View):
    def get(self, request):
        # 1. 获取用户画像，增加安全性校验
        userprofile = UserProfile.objects.filter(user=request.user).first()
        if not userprofile:
            return render(request, 'profile.html', {'error': '未找到用户配置'})

        # --- 2. 数据清洗与 ID 提取 ---
        # 收藏夹：去重处理
        raw_collect_ids = userprofile.collected_movie_ids or []
        collect_ids = []
        _seen = set()
        for i in raw_collect_ids:
            try:
                mid = int(i)  # 确保转换为整数以匹配数据库类型
                if mid not in _seen:
                    collect_ids.append(mid)
                    _seen.add(mid)
            except (ValueError, TypeError):
                continue

        # 历史记录：不去重，保留重复，取最后 50 条并反转（最近的排在前）
        raw_click_ids = userprofile.clicked_movie_ids or []
        history_ids = []
        for i in reversed(raw_click_ids[-50:]):
            try:
                history_ids.append(int(i))
            except (ValueError, TypeError):
                continue

        # --- 3. 批量查询优化 (核心：变 100+ 次查询为 2 次查询) ---
        all_query_ids = list(set(collect_ids + history_ids))

        # 批量获取电影对象映射表
        movies_map = {m.movie_id: m for m in Movie.objects.filter(movie_id__in=all_query_ids)}

        # 批量获取观看时间映射表
        watch_records = MovieWatchRecord.objects.filter(
            user=request.user,
            movie_id__in=all_query_ids
        ).values('movie_id', 'watch_time')
        watch_map = {r['movie_id']: r['watch_time'] for r in watch_records}

        # --- 4. 构造前端数据列表 ---

        def build_display_data(m_id):
            movie = movies_map.get(m_id)
            if not movie:
                return None

            return {
                'id': m_id,
                'title': movie.title,
                'year': movie.year,
                'rating': round(float(movie.avg_rating), 1) if movie.avg_rating else 0,
                'cover_url': get_image.get_image_url(m_id, use_thumbnail=True),
                'view_date': watch_map.get(m_id, '该电影未记录观影时间')
            }

        # 构造最终列表
        favorite_movies_list = [build_display_data(mid) for mid in collect_ids if mid in movies_map]
        # history_movies_list 会根据 history_ids 的重复项生成对应的重复电影卡片
        history_movies_list = [build_display_data(mid) for mid in history_ids if mid in movies_map]

        # ==================== Feature 3: 增强画像标签 ====================

        # --- 偏好类型 Top3 ---
        # 获取用户所有交互过的电影 ID
        all_interacted_ids = set(raw_click_ids) | set(raw_collect_ids)
        all_interacted_ids = {int(i) for i in all_interacted_ids if i}

        genre_counter = Counter()
        if all_interacted_ids:
            interacted_movies = Movie.objects.filter(movie_id__in=all_interacted_ids)
            for m in interacted_movies:
                if m.genres:
                    # 支持逗号和竖线分隔的类型字段
                    parts = m.genres.replace('|', ',').split(',')
                    for p in parts:
                        p = p.strip()
                        if p:
                            genre_counter[p] += 1

        from utils.genres import Genres
        top_genres_cn = []
        for en_genre, _ in genre_counter.most_common(3):
            cn_name = Genres.GENRE_MAP.get(en_genre, en_genre)
            top_genres_cn.append(cn_name)

        # 冷启动问卷中选择的偏好类型（中文翻译）
        preferred_genres_cn = []
        if userprofile.preferred_genres:
            for g in userprofile.preferred_genres:
                preferred_genres_cn.append(Genres.GENRE_MAP.get(g, g))

        # --- 平均评分 ---
        from django.db.models import Avg
        avg_rating_result = MovieRating.objects.filter(
            user=request.user
        ).aggregate(avg=Avg('rating'))['avg']
        avg_rating = round(float(avg_rating_result), 1) if avg_rating_result else 0

        # --- 用户活跃等级 ---
        total_actions = userprofile.point_count
        if total_actions < 30:
            activity_level = '轻度影迷 🌱'
        elif total_actions < 100:
            activity_level = '中度影迷 🎬'
        else:
            activity_level = '重度影迷 🔥'

        # --- 近期最爱影片 ---
        fav_movie_title = None
        try:
            conn = Recommender.get_redis_conn()
            redis_actions = conn.lrange(f"user_history:{request.user.id}", 0, -1)
            if redis_actions:
                import json as _json
                actions_list = [_json.loads(a) for a in redis_actions]
                if actions_list:
                    best_action = max(actions_list, key=lambda a: {
                        'click': 0.3, 'collect': 0.7, 'rating': 1.0
                    }.get(a.get('type', 'click'), 0.3))
                    best_mid = best_action.get('mid')
                    if best_mid:
                        from movies.models import Movie as M
                        try:
                            fav_movie_title = M.objects.get(movie_id=best_mid).title
                        except Exception:
                            pass
        except Exception:
            pass

        # --- 趣味称号 ---
        fun_titles = {
            'Sci-Fi': '🚀 宇宙探索者',
            'Action': '💥 动作达人',
            'Thriller': '🔍 悬疑探长',
            'Crime': '🕵️ 犯罪克星',
            'Horror': '👻 恐怖勇士',
            'Romance': '💕 浪漫诗人',
            'Comedy': '😄 快乐源泉',
            'Animation': '🎨 动画达人',
            'Drama': '🎭 剧情品鉴师',
            'Adventure': '🗺️ 冒险家',
            'War': '⚔️ 战争史学家',
            'Documentary': '📚 求知学者',
        }
        fun_title = '🎬 电影爱好者'
        if genre_counter:
            top_en = genre_counter.most_common(1)[0][0]
            fun_title = fun_titles.get(top_en, fun_title)

        # ==================== Feature 5: A/B 实验数据 ====================
        rec_group = getattr(userprofile, 'rec_group', 'A')
        group_label = {
            'A': '对照组 (原推荐策略)',
            'B': '实验组 (多样性优化)'
        }.get(rec_group, rec_group)

        # 用户个人统计
        from user.models import RecEvent as RE
        user_click_count = RE.objects.filter(
            user=request.user, rec_group=rec_group, event_type='click'
        ).count()
        user_collect_count = RE.objects.filter(
            user=request.user, rec_group=rec_group, event_type='collect'
        ).count()

        # 系统级对比（简化：人均收藏数）
        from django.db.models import Count
        group_stats = RE.objects.values('rec_group', 'event_type').annotate(
            cnt=Count('id')
        )
        a_collect = sum(s['cnt'] for s in group_stats if s['rec_group'] == 'A' and s['event_type'] == 'collect')
        b_collect = sum(s['cnt'] for s in group_stats if s['rec_group'] == 'B' and s['event_type'] == 'collect')
        a_users = UserProfile.objects.filter(rec_group='A').count() or 1
        b_users = UserProfile.objects.filter(rec_group='B').count() or 1

        rating_count = MovieRating.objects.filter(user=request.user).count()

        # --- 返回结果 ---
        contents = {
            'favorite_movies': favorite_movies_list,
            'history_movies': history_movies_list,
            'collect_count': len(collect_ids),
            'history_count': len(raw_click_ids),
            'rating_count': rating_count,
            'email_push': userprofile.is_send,
            'is_explore': userprofile.is_explore,

            # Feature 3: 增强画像
            'top_genres': top_genres_cn,
            'preferred_genres_cn': preferred_genres_cn,
            'avg_rating': avg_rating,
            'activity_level': activity_level,
            'fav_movie_title': fav_movie_title,
            'fun_title': fun_title,

            # Genre editing in settings (filter out non-selectable entries)
            'all_genres': [(k, v) for k, v in Genres.GENRE_MAP.items() if k not in ('(no genres listed)', "Children's")],
            'user_preferred_genres': userprofile.preferred_genres or [],

            # Feature 5: A/B 实验
            'rec_group': rec_group,
            'group_label': group_label,
            'user_click_count': user_click_count,
            'user_collect_count': user_collect_count,
            'a_per_capita': round(a_collect / a_users, 1) if a_users > 0 else 0,
            'b_per_capita': round(b_collect / b_users, 1) if b_users > 0 else 0,
            'a_bar_width': min(100, int((a_collect / max(a_users, 1)) * 50)),
            'b_bar_width': min(100, int((b_collect / max(b_users, 1)) * 50)),
        }
        return render(request, 'profile.html', context=contents)



class SendInfoView(LoginRequiredMixin,View):
    from movies.models import Movie
    from user.models import UserProfile

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'msg': '未登录'})

        try:
            data = json.loads(request.body)
            is_send = bool(data.get('is_send', False))

            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.is_send = is_send
            profile.save()

            user = request.user

            # 获取电影ID
            clicked_ids = set(profile.clicked_movie_ids or [])
            collected_ids = set(profile.collected_movie_ids or [])

            all_ids = list(clicked_ids | collected_ids)

            # 查电影
            movies = Movie.objects.filter(movie_id__in=all_ids)[:10]

            movie_list = [
                {
                    "title": m.title,
                    "genre": m.genres,
                    "rating": m.avg_rating if m.avg_rating else 0
                }
                for m in movies
            ]

            if not movie_list:
                return JsonResponse({'status': 'error', 'msg': '无推荐电影'})

            sender = MovieEmailSender()

            result = sender.send_recommendation(
                receiver_email=user.email,
                username=user.username,
                movie_list=movie_list
            )

            print("邮件发送结果:", result)

            return JsonResponse({
                'status': 'success',
                'is_send': profile.is_send
            })

        except Exception as e:
            print("报错:", e)
            return JsonResponse({
                'status': 'error',
                'msg': str(e)
            })



class RankView(LoginRequiredMixin,View):
    """
    电影排行榜视图
    优化点：
    1. 使用 values() 减少ORM开销
    2. 批量查询替代N+1查询
    3. Redis缓存整页数据和NCF推荐结果
    4. 限制每榜50条数据
    """

    def get(self, request):
        print("后端收到请求")

        # 尝试从缓存获取整页数据（5分钟缓存）
        cache_key = f'rank_data_{request.user.id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            print("命中缓存，直接返回")
            return render(request, 'rank.html', context=cached_data)

        # 电影简介数据
        profiles = [
            "太阳即将毁灭，人类在地球表面建造出巨大的推进器，寻找新的家园。然而宇宙之路危机四伏，为了拯救地球，流浪地球时代的年轻人再次挺身而出...",
            "深海勘探队在马里亚纳海沟发现不明生物信号，随着下潜深度增加，队员们逐渐发现这片黑暗深渊中隐藏着足以改变人类认知的秘密...",
            "一位能够穿越时间的特工，必须在时间线的各个节点阻止一场足以毁灭历史的阴谋。每一次选择都会创造新的时间分支...",
            "繁华都市的夜晚，几个孤独灵魂的命运交织。霓虹灯下的邂逅，地铁里的错过，便利店前的等待...",
            "银河系边缘的殖民地突然失联，调查小队发现这是一个古老文明觉醒的前兆。人类将面临有史以来最大的生存危机...",
        ]

        # ==================== 1. 评分榜（平均评分最高）====================
        rating_movies = Movie.objects.values(
            'movie_id', 'title', 'genres', 'avg_rating', 'year'
        ).order_by('-avg_rating')[:50]

        ratingmovie = []
        for idx, movie in enumerate(rating_movies):
            genres = movie['genres']
            if isinstance(genres, str):
                genres = [g.strip() for g in genres.split(',')]
            elif genres is None:
                genres = []

            # 修复：5分制直接四舍五入
            rating_val = movie['avg_rating'] or 0
            star_count = round(rating_val)
            star_count = max(0, min(5, star_count))
            stars = '★' * star_count + '☆' * (5 - star_count)

            ratingmovie.append({
                'title': movie['title'],
                'genre': genres,
                'rating': round(rating_val, 1),
                'year': movie['year'] or '未知',
                'profile': profiles[idx % len(profiles)],
                'cover_url': get_image.get_image_url(movie["movie_id"], use_thumbnail=True),
                'stars': stars,
                'movie_id':movie['movie_id'],
            })

        # ==================== 2. 热度榜（点击+收藏最多）====================
        # 获取所有用户行为数据（2次查询）
        user_profiles = UserProfile.objects.values('clicked_movie_ids', 'collected_movie_ids')

        # 统计每部电影的热度
        movie_counter = Counter()
        for profile in user_profiles:
            if profile['clicked_movie_ids']:
                movie_counter.update(profile['clicked_movie_ids'])
            if profile['collected_movie_ids']:
                movie_counter.update(profile['collected_movie_ids'])

        # 取热度最高的50个电影ID
        hot_movie_ids = [movie_id for movie_id, _ in movie_counter.most_common(50)]

        # 批量查询电影详情（1次查询替代50次get()）
        hot_movies_map = {
            m['movie_id']: m for m in
            Movie.objects.filter(movie_id__in=hot_movie_ids).values(
                'movie_id', 'title', 'genres', 'avg_rating', 'year'
            )
        }

        # 按热度顺序组装数据
        hot_movies = []
        for idx, movie_id in enumerate(hot_movie_ids):
            movie = hot_movies_map.get(movie_id)
            if not movie:
                continue

            genres = movie['genres']
            if isinstance(genres, str):
                genres = [g.strip() for g in genres.split(',')]
            elif genres is None:
                genres = []

            # 修复：5分制直接四舍五入
            rating_val = movie['avg_rating'] or 0
            star_count = round(rating_val)
            star_count = max(0, min(5, star_count))
            stars = '★' * star_count + '☆' * (5 - star_count)

            hot_movies.append({
                'title': movie['title'],
                'genre': genres,
                'rating': round(rating_val, 1),
                'year': movie['year'] or '未知',
                'profile': profiles[idx % len(profiles)],
                'cover_url': get_image.get_image_url(movie_id, use_thumbnail=True),
                'hot_score': movie_counter[movie_id],
                'stars': stars,
                'movie_id': movie_id,
            })

        # ==================== 3. NCF推荐榜（基于神经网络协同过滤）====================
        ncf_cache_key = f'ncf_recommendations_{request.user.id}'
        ncf_movie_list = cache.get(ncf_cache_key)

        ncf_reason = None
        if ncf_movie_list is None:
            # 获取NCF推荐结果（计算最慢，单独缓存）
            ncf_result, source_title = Recommender.get_ncf_recommendations(request.user)
            if source_title:
                ncf_reason = f'因为你喜欢《{source_title}》，为你找到以下推荐'

            # 统一转换为列表
            if hasattr(ncf_result, 'tolist'):
                ncf_result = ncf_result.tolist()
            elif not isinstance(ncf_result, list):
                ncf_result = list(ncf_result)

            # 强制全部转为字典格式，避免对象和字典混用
            ncf_movie_list = []
            for item in ncf_result[:50]:
                if isinstance(item, Movie):
                    # Movie对象转字典
                    ncf_movie_list.append({
                        'movie_id': item.movie_id,
                        'title': item.title,
                        'genres': item.genres,
                        'avg_rating': item.avg_rating,
                        'year': item.year,

                    })
                elif isinstance(item, dict):
                    ncf_movie_list.append(item)
                elif isinstance(item, (int, str, float)):
                    # 只有ID，后续补充详情
                    ncf_movie_list.append({'movie_id': int(item)})

            # 缓存NCF结果（5分钟）
            cache.set(ncf_cache_key, ncf_movie_list, 300)

        # 检查哪些电影需要补充详情（没有title的）
        missing_ids = []
        for movie in ncf_movie_list:
            if isinstance(movie, dict) and not movie.get('title') and movie.get('movie_id'):
                missing_ids.append(movie['movie_id'])

        # 批量查询缺失的电影详情
        if missing_ids:
            details = {
                m['movie_id']: m for m in
                Movie.objects.filter(movie_id__in=missing_ids).values(
                    'movie_id', 'title', 'genres', 'avg_rating', 'year'
                )
            }
            # 合并详情
            for movie in ncf_movie_list:
                if isinstance(movie, dict):
                    mid = movie.get('movie_id')
                    if mid in details:
                        movie.update(details[mid])

        # 组装最终NCF数据
        ncf_movies = []
        for idx, movie in enumerate(ncf_movie_list):
            if not isinstance(movie, dict) or not movie.get('title'):
                continue

            genres = movie.get('genres', [])
            if isinstance(genres, str):
                genres = [g.strip() for g in genres.split(',')]
            elif genres is None:
                genres = []

            # 修复：5分制直接四舍五入
            rating_val = movie.get('avg_rating', 0) or 0
            star_count = round(rating_val)
            star_count = max(0, min(5, star_count))
            stars = '★' * star_count + '☆' * (5 - star_count)

            ncf_score = round(5.0 - idx * 0.1, 2)
            recommend_percent = round((ncf_score / 5.0) * 100, 1)
            ncf_movies.append({
                'title': movie['title'],
                'genre': genres,
                'rating': round(rating_val, 1),
                'year': movie.get('year', '未知'),
                'profile': profiles[idx % len(profiles)],
                'cover_url': get_image.get_image_url(movie["movie_id"], use_thumbnail=True),
                'ncf_score': ncf_score,
                'recommend_percent': recommend_percent,
                'stars': stars,
                'movie_id': movie['movie_id'],
            })

        # ==================== 组装上下文并缓存 ====================
        contents = {
            'rating_movies': ratingmovie,
            'hot_movies': hot_movies,
            'ncf_movies': ncf_movies,
            'ncf_reason': ncf_reason,
        }

        # 整页缓存5分钟
        cache.set(cache_key, contents, 300)

        return render(request, 'rank.html', context=contents)


# Feature 5: A/B 实验数据 API
class ExpStatsView(LoginRequiredMixin, View):
    def get(self, request):
        from user.models import RecEvent as RE

        group_stats = RE.objects.values('rec_group', 'event_type').annotate(
            cnt=Count('id')
        )

        a_collect = sum(s['cnt'] for s in group_stats if s['rec_group'] == 'A' and s['event_type'] == 'collect')
        b_collect = sum(s['cnt'] for s in group_stats if s['rec_group'] == 'B' and s['event_type'] == 'collect')
        a_click = sum(s['cnt'] for s in group_stats if s['rec_group'] == 'A' and s['event_type'] == 'click')
        b_click = sum(s['cnt'] for s in group_stats if s['rec_group'] == 'B' and s['event_type'] == 'click')

        a_users = UserProfile.objects.filter(rec_group='A').count() or 1
        b_users = UserProfile.objects.filter(rec_group='B').count() or 1

        return JsonResponse({
            'status': 'success',
            'data': {
                'labels': ['A组 (对照组)', 'B组 (实验组)'],
                'collect_per_capita': [
                    round(a_collect / a_users, 2),
                    round(b_collect / b_users, 2),
                ],
                'click_per_capita': [
                    round(a_click / a_users, 2),
                    round(b_click / b_users, 2),
                ],
                'a_users': a_users,
                'b_users': b_users,
            }
        })