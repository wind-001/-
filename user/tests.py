import os
import django
from django.test import TestCase
from django.contrib.auth import get_user_model  # 关键：动态获取当前生效的用户模型
from user.models import UserProfile  # 替换成你的 UserProfile 模型路径

# 1. 初始化 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MoviesRec.settings')
django.setup()

# 获取项目中实际使用的用户模型（自动适配 AUTH_USER_MODEL 配置）
User = get_user_model()

# 方式1：作为 Django 测试用例运行（推荐）
class ClearUserAndProfileTest(TestCase):
    def test_clear_users_and_profiles(self):
        """清空所有 User 和关联的 UserProfile"""
        # 方式A：利用级联删除（推荐，一步到位）
        User.objects.all().delete()  # 现在使用的是项目自定义的 User 模型

        # 方式B：手动先删 Profile 再删 User（效果和A一致，更直观）
        # UserProfile.objects.all().delete()
        # User.objects.all().delete()

        # 验证：确认已清空
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(UserProfile.objects.count(), 0)
        print("User 剩余数量：", User.objects.count())       # 输出 0
        print("UserProfile 剩余数量：", UserProfile.objects.count())  # 输出 0

# 方式2：作为独立脚本运行
if __name__ == "__main__":
    # 清空数据
    User.objects.all().delete()
    # 验证
    print("User 剩余数量：", User.objects.count())       # 输出 0
    print("UserProfile 剩余数量：", UserProfile.objects.count())  # 输出 0