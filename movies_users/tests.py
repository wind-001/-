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
from movies_users.models import UserProfile


def import_users(json_file_path=r"../movies_users.json"):
    """
    从JSON文件导入用户数据到UserProfile模型
    :param json_file_path: JSON文件路径
    """
    try:
        # 读取JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            users_data = json.load(f)

        # 统计导入数量
        imported_count = 0
        skipped_count = 0

        # 遍历数据并导入
        for key, user_info in users_data.items():
            # 使用update_or_create避免重复导入
            user, created = UserProfile.objects.update_or_create(
                user_id=user_info["user_id"],  # 按user_id唯一匹配
                defaults={
                    "gender": user_info["gender"],
                    "age": user_info["age"],
                    "age_group": user_info["age_group"],
                    "occupation_code": user_info["occupation_code"],
                    "occupation": user_info["occupation"],
                    "zip_code": user_info["zip_code"]
                }
            )

            if created:
                imported_count += 1
                print(f"新增用户：{user}")
            else:
                skipped_count += 1
                print(f"跳过已存在的用户：{user}")

        # 导入完成统计
        print("\n===== 用户数据导入完成 =====")
        print(f"总计处理：{len(users_data)} 条")
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
    import_users()