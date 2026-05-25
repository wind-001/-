# 导入Django环境（必须放在最开头）
import os
import sys
import json
import warnings
from datetime import datetime
import pytz
from django.utils import timezone
from django.db import transaction, IntegrityError
from django.db.models import Prefetch

# 将项目根目录加入Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MoviesRec.settings')  # 替换为项目名

# 导入Django核心模块和模型
import django

django.setup()
from ratings.models import Rating
from movies.models import Movie
from movies_users.models import UserProfile

# 抑制时区警告（可选，减少日志输出）
warnings.filterwarnings('ignore', message='DateTimeField .* received a naive datetime')

# 批量配置（可根据服务器性能调整）
BATCH_SIZE = 1000  # 每批处理1000条数据
PRINT_INTERVAL = 10000  # 每处理10000条打印一次进度（减少IO）


def import_ratings_optimized(json_file_path=r"../ratings.json"):
    """
    优化版评分数据导入：批量操作+缓存查询+事务封装
    适配大数据量导入，大幅提升速度
    """
    start_time = datetime.now()
    print(f"开始导入评分数据，时间：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"批量大小：{BATCH_SIZE}，进度打印间隔：{PRINT_INTERVAL}")

    try:
        # 1. 一次性读取JSON文件（避免多次IO）
        with open(json_file_path, 'r', encoding='utf-8') as f:
            # 大数据量建议用逐行读取（如果JSON是行式结构）
            # 这里兼容标准JSON和行式JSON
            try:
                ratings_data = json.load(f)  # 标准JSON（字典格式）
                data_list = list(ratings_data.values())
            except json.JSONDecodeError:
                # 行式JSON（每行一个JSON对象）
                data_list = []
                for line in f:
                    line = line.strip()
                    if line:
                        data_list.append(json.loads(line))

        total_count = len(data_list)
        print(f"总计待处理评分数据：{total_count} 条")

        # 2. 预加载所有用户和电影数据到内存（缓存查询，仅2次数据库查询）
        print("预加载用户和电影数据到内存...")
        # 预加载所有用户：{user_id: UserProfile对象}
        user_map = {u.user_id: u for u in UserProfile.objects.all().only('user_id')}
        # 预加载所有电影：{movie_id: Movie对象}
        movie_map = {m.movie_id: m for m in Movie.objects.all().only('movie_id')}
        print(f"预加载完成：用户{len(user_map)}个，电影{len(movie_map)}部")

        # 3. 数据预处理+批量分组
        target_timezone = pytz.timezone(timezone.get_current_timezone_name())
        batch_data = []  # 批量存储待写入的Rating对象
        skip_exist_ids = set()  # 缓存已存在的(用户ID,电影ID)组合，避免重复检查
        stats = {
            "total": total_count,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "batch_num": 0
        }

        # 先查询所有已存在的评分组合（仅1次查询）
        print("查询已存在的评分记录...")
        existing_ratings = Rating.objects.all().values_list('user_id', 'movie_id')
        skip_exist_ids = set(existing_ratings)
        print(f"已存在的评分记录：{len(skip_exist_ids)} 条")

        # 4. 批量处理+事务写入
        def process_batch(batch):
            """处理单批数据，事务内批量写入"""
            nonlocal stats
            if not batch:
                return
            try:
                with transaction.atomic():  # 事务封装：批量提交
                    Rating.objects.bulk_create(
                        batch,
                        batch_size=BATCH_SIZE,
                        ignore_conflicts=True  # 忽略唯一键冲突（替代update_or_create）
                    )
                stats["success"] += len(batch)
                stats["batch_num"] += 1
                if stats["batch_num"] % (PRINT_INTERVAL // BATCH_SIZE) == 0:
                    print(
                        f"已处理 {stats['success'] + stats['skipped'] + stats['failed']}/{stats['total']} 条，成功{stats['success']}，跳过{stats['skipped']}，失败{stats['failed']}")
            except IntegrityError as e:
                # 批量写入失败时降级为逐条处理（保证数据不丢失）
                for item in batch:
                    try:
                        with transaction.atomic():
                            item.save(ignore_conflicts=True)
                        stats["success"] += 1
                    except Exception:
                        stats["failed"] += 1
                stats["batch_num"] += 1

        # 遍历数据并分组
        print("开始批量处理数据...")
        for idx, rating_info in enumerate(data_list):
            # 跳过进度打印，仅间隔输出
            if idx % PRINT_INTERVAL == 0 and idx > 0:
                print(f"进度：已处理 {idx}/{total_count} 条")

            # 检查用户/电影是否存在（内存查询，无数据库IO）
            user_id = rating_info.get("user_id")
            movie_id = rating_info.get("movie_id")
            if user_id not in user_map or movie_id not in movie_map:
                stats["failed"] += 1
                continue

            # 检查是否已存在（内存查询）
            if (user_id, movie_id) in skip_exist_ids:
                stats["skipped"] += 1
                continue

            # 时间转换（带时区）
            naive_dt = datetime.strptime(rating_info["datetime"], "%Y-%m-%d %H:%M:%S")
            aware_dt = target_timezone.localize(naive_dt)

            # 构建Rating对象（仅内存操作，未写入数据库）
            rating_obj = Rating(
                user_id=user_id,
                movie_id=movie_id,
                rating=rating_info["rating"],
                timestamp=rating_info["timestamp"],
                datetime=aware_dt,
                line_number=rating_info.get("line_number")
            )
            batch_data.append(rating_obj)

            # 达到批量大小则写入
            if len(batch_data) >= BATCH_SIZE:
                process_batch(batch_data)
                batch_data = []  # 清空批次

        # 处理剩余数据
        if batch_data:
            process_batch(batch_data)

        # 最终统计
        end_time = datetime.now()
        cost_time = (end_time - start_time).total_seconds()
        print("\n===== 评分数据导入完成 =====")
        print(f"总计数据：{stats['total']} 条")
        print(f"成功导入：{stats['success']} 条")
        print(f"跳过已存在：{stats['skipped']} 条")
        print(f"导入失败：{stats['failed']} 条")
        print(f"总耗时：{cost_time:.2f} 秒（{cost_time / 60:.2f} 分钟）")
        print(f"平均速度：{stats['total'] / cost_time:.2f} 条/秒（成功：{stats['success'] / cost_time:.2f} 条/秒）")

    except FileNotFoundError:
        print(f"错误：未找到JSON文件 {json_file_path}")
    except KeyError as e:
        print(f"错误：JSON数据缺少必要字段 {e}")
    except Exception as e:
        print(f"导入失败：{str(e)}")
        # 打印详细异常栈（便于排查）
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行优化版导入函数
    import_ratings_optimized()