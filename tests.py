import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MoviesRec.settings")
django.setup()

from django.db.models import Avg
from movies.models import Movie

def update_movie_avg_rating():
    # 批量更新所有电影的 avg_rating，并保留 1 位小数
    movies = Movie.objects.annotate(calculated_avg=Avg('ratings__rating'))
    for movie in movies:
        avg = movie.calculated_avg or 0.0
        movie.avg_rating = round(avg, 1)  # 这里 ✅ 保留 1 位小数
        movie.save(update_fields=['avg_rating'])
    print("所有电影的 avg_rating 更新完成（已保留 1 位小数）！")

if __name__ == "__main__":
    update_movie_avg_rating()