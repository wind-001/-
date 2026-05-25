from apscheduler.schedulers.background import BackgroundScheduler


from user.models import UserProfile
from utils.recommender.recommend import Recommender
from verification.emailCode.EmailSendMovies import MovieEmailSender


scheduler = BackgroundScheduler()


def send_weekly_recommendation():
    print("🚀 开始执行周一推荐任务")

    sender = MovieEmailSender()

    users = UserProfile.objects.filter(is_monday_push=True, is_send=True)

    for profile in users:
        user = profile.user

        # movie_list = [
        #     {"title": "盗梦空间", "genre": "科幻", "rating": 9.2},
        #     {"title": "星际穿越", "genre": "科幻", "rating": 9.4},
        #     {"title": "阿凡达", "genre": "冒险", "rating": 8.8},
        # ]

        movie_list, _ = Recommender.get_ncf_recommendations(user)
        movie_list = [
            {
                "title": m.title,
                "genre": m.genres,
                "rating": m.avg_rating
            }
            for m in movie_list
        ]
        sender.send_recommendation(
            receiver_email=user.email,
            username=user.username,
            movie_list=movie_list
        )

    print("✅ 周一推荐发送完成")


def start_scheduler():
    scheduler.add_job(
        send_weekly_recommendation,
        'cron',
        day_of_week='mon',
        hour=8,
        minute=0
    )
    # 演示,先按照2分钟执行一次
    # scheduler.add_job(send_weekly_recommendation, 'interval', seconds=120)

    scheduler.start()