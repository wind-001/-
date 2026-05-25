# 导入Django环境（必须放在最开头）
import os
import sys
import json

# 将项目根目录加入Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MoviesRec.settings')  # 替换为你的Django项目名

# 导入Django核心模块和模型
import django

django.setup()
from movies.models import Movie


def import_movies(json_file_path=r"../movies.json"):
    """
    从JSON文件导入电影数据到Movie模型
    :param json_file_path: JSON文件路径
    """
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            movies_data = json.load(f)

        # 统计导入数量
        imported_count = 0
        skipped_count = 0

        # 遍历数据并导入
        for key, movie_info in movies_data.items():
            # 核心：将genres数组转为逗号分隔的字符串
            genres_str = ",".join(movie_info.get("genres", []))

            # 使用update_or_create避免重复导入
            movie, created = Movie.objects.update_or_create(
                movie_id=movie_info["movie_id"],  # 按movie_id唯一匹配
                defaults={
                    "title": movie_info["title"],
                    "year": movie_info["year"],
                    "genres": genres_str
                }
            )

            if created:
                imported_count += 1
                print(f"新增电影：{movie.full_title}")
            else:
                skipped_count += 1
                print(f"跳过已存在的电影：{movie.full_title}")

        # 导入完成统计
        print("\n===== 电影数据导入完成 =====")
        print(f"总计处理：{len(movies_data)} 条")
        print(f"新增导入：{imported_count} 条")
        print(f"跳过已存在：{skipped_count} 条")

    except FileNotFoundError:
        print(f"错误：未找到JSON文件 {json_file_path}")
    except KeyError as e:
        print(f"错误：JSON数据缺少必要字段 {e}")
    except Exception as e:
        print(f"导入失败：{str(e)}")


if __name__ == "__main__":
    # 运行导入函数
    import_movies()