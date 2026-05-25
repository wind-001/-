from django.db import models
# 核心修正：导入正确的校验器模块
from django.core.validators import MinValueValidator, MaxValueValidator


class UserProfile(models.Model):
    """
    电影用户信息模型（movies_users应用）
    存储用户的性别、年龄、职业、邮编等基础信息
    """
    # 主键：用户ID（与JSON中的user_id完全对应）
    user_id = models.IntegerField(primary_key=True, verbose_name="用户ID")

    # 性别：枚举类型（F-女性，M-男性），限制可选值
    GENDER_CHOICES = (
        ("F", "Female"),
        ("M", "Male"),
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name="性别",
        help_text="F=女性，M=男性"
    )

    # 年龄：整数类型，设置合理范围（0-120岁）
    # 修正：使用正确导入的校验器
    age = models.IntegerField(
        verbose_name="年龄",
        validators=[
            MinValueValidator(0),  # 最小值0
            MaxValueValidator(120)  # 最大值120
        ]
    )

    # 年龄组：枚举类型（覆盖常见年龄段），与JSON中的age_group对应
    AGE_GROUP_CHOICES = (
        ("Under 18", "Under 18"),
        ("18-24", "18-24"),
        ("25-34", "25-34"),
        ("35-44", "35-44"),
        ("45-49", "45-49"),
        ("50-55", "50-55"),
        ("56+", "56+"),
    )
    age_group = models.CharField(
        max_length=10,
        choices=AGE_GROUP_CHOICES,
        verbose_name="年龄组"
    )

    # 职业编码：字符串类型（JSON中为数字字符串），保留原始编码
    occupation_code = models.CharField(max_length=5, verbose_name="职业编码")

    # 职业名称：字符串类型，存储完整职业描述
    occupation = models.CharField(max_length=50, verbose_name="职业名称")

    # 邮编：字符串类型（兼容含字母/特殊字符的邮编）
    zip_code = models.CharField(max_length=20, verbose_name="邮政编码")

    class Meta:
        # 数据库表名
        db_table = "movies_users"
        # 后台显示名称
        verbose_name = "电影用户信息"
        verbose_name_plural = "电影用户信息"
        # 默认排序：按用户ID升序
        ordering = ["user_id"]
        # 索引优化：提升按性别、年龄组、职业查询的效率
        indexes = [
            models.Index(fields=["gender"]),
            models.Index(fields=["age_group"]),
            models.Index(fields=["occupation"]),
        ]

    def __str__(self):
        """返回用户的易读描述"""
        return f"用户{self.user_id} ({self.gender}) - {self.age}岁 - {self.occupation}"