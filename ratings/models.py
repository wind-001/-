from django.db import models
# 导入movies应用的Movie模型
from movies.models import Movie
# 导入movies_users应用的UserProfile模型
from movies_users.models import UserProfile


class Rating(models.Model):
    """用户电影评分模型类（修正命名冲突版）"""
    # 核心修正：外键保留，删除重名的@property
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        related_name="ratings",
        verbose_name="用户",
        db_column="user_id"  # 数据库字段名显式为user_id
    )

    movie = models.ForeignKey(
        Movie,
        on_delete=models.PROTECT,
        related_name="ratings",
        verbose_name="电影",
        db_column="movie_id"  # 数据库字段名显式为movie_id
    )

    # 评分值（支持小数，如5.0、3.0）
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        verbose_name="评分"
    )

    # 原始时间戳（保留JSON中的原始数据）
    timestamp = models.BigIntegerField(verbose_name="时间戳")

    # 格式化时间（由timestamp转换而来）
    datetime = models.DateTimeField(verbose_name="评分时间")

    # 原始文件行号（可选字段）
    line_number = models.IntegerField(blank=True, null=True, verbose_name="原始行号")

    class Meta:
        db_table = "ratings"
        verbose_name = "评分"
        verbose_name_plural = "评分"
        # 联合唯一索引：一个用户对一部电影只能有一个评分
        unique_together = ("user", "movie")
        ordering = ["-datetime"]
        # 索引优化
        indexes = [
            models.Index(fields=["user", "rating"]),
            models.Index(fields=["movie", "rating"]),
            models.Index(fields=["datetime"]),
        ]

    def __str__(self):
        """优化显示：避免使用重名属性"""
        return f"用户{self.user.user_id}（{self.user.occupation}）对《{self.movie.title}》的评分：{self.rating}"

    # 核心修正：删除重名的@property user_id/movie_id
    # Django已自动为外键生成xxx_id访问器，无需手动定义
    # 如需兼容JSON字段，可改用其他名称，例如：
    @property
    def user_identifier(self):
        """兼容JSON中的user_id字段（重命名避免冲突）"""
        return self.user.user_id

    @property
    def movie_identifier(self):
        """兼容JSON中的movie_id字段（重命名避免冲突）"""
        return self.movie.movie_id