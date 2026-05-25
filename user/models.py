from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User (AbstractUser):
    email = models.EmailField()
    class Meta:
        db_table = 'user'


class UserProfile(models.Model):
    is_send = models.BooleanField(default=False, verbose_name="是否发送邮件")
    # 推荐引擎个性化配置
    is_explore = models.BooleanField(default=False, verbose_name="开启探索模式")
    is_monday_push = models.BooleanField(default=False, verbose_name="周一特刊推送")

    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='userprofile')

    # 最低接受评分
    min_rating = models.FloatField(default=3.0)

    # 1. 基础画像(冷启动)
    preferred_genres = models.JSONField(default=list, verbose_name="偏好类型")
    cold_start_completed = models.BooleanField(default=False)

    # 2. 行为统计
    point_count = models.IntegerField(default=0, verbose_name="点击次数")

    # 3. 行为序列存储 (存储电影 ID 列表)
    # 记录点击过的电影 ID，用于计算实时 Embedding 均值
    clicked_movie_ids = models.JSONField(default=list, verbose_name="点击历史序列")

    # 记录收藏的电影 ID，这部分权重在 NCF 训练中可以设得比点击更高
    collected_movie_ids = models.JSONField(default=list, verbose_name="收藏序列")

    # 4. 实时向量持久化 (可选，用于同步 Redis 结果)
    # 存储为二进制或字符串，避免每次从 Redis 读不到时丢失状态
    last_user_embedding = models.BinaryField(null=True, blank=True, verbose_name="用户嵌入向量")


    # 用户活跃度
    USER_LEVEL_CHOICES = [
        ('new', '新影迷'),
        ('active', '资深影迷'),
        ('pro', '电影发烧友')
    ]

    user_level = models.CharField(
        max_length=10,
        choices=USER_LEVEL_CHOICES,
        default='new'
    )

    # 是否完成冷启动调查
    cold_start_completed = models.BooleanField(default=False)

    # Feature 5: A/B 测试分组
    rec_group = models.CharField(max_length=1, default='A', verbose_name="实验分组")

    # 创建时间
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


# Feature 5: A/B 测试行为记录模型
class RecEvent(models.Model):
    EVENT_TYPES = [
        ('click', '点击'),
        ('collect', '收藏'),
        ('rating', '评分'),
        ('impression', '展示'),
    ]

    SOURCE_TYPES = [
        ('homepage', '首页推荐'),
        ('rank', '排行榜'),
        ('detail_rec', '详情页推荐'),
        ('search', '搜索'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey('movies.Movie', on_delete=models.CASCADE)
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES)
    rec_group = models.CharField(max_length=1)
    source = models.CharField(max_length=20, choices=SOURCE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "实验事件记录"
        verbose_name_plural = "实验事件记录"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rec_group', 'event_type']),
            models.Index(fields=['user', 'created_at']),
        ]



class MovieWatchRecord(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="观看用户",
        primary_key=False,  # 必须显式设置，因为 ForeignKey 默认不能作为主键
    )
    movie_id = models.IntegerField(
        verbose_name="电影ID",
        primary_key=False,  # 必须显式设置
    )
    watch_time = models.DateTimeField(
        auto_now=True,  # 每次保存时自动更新为当前时间
        verbose_name="观看时间"
    )
    class Meta:
        verbose_name = "电影观看记录"
        verbose_name_plural = "电影观看记录"
        unique_together = ('user', 'movie_id')  # 联合唯一约束（相当于联合主键）
        ordering = ['-watch_time']  # 默认按观看时间降序排列
    def __str__(self):
        return f"{self.user.username} 观看了电影 {self.movie_id} 于 {self.watch_time}"

class MovieRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie_id = models.IntegerField()

    rating = models.IntegerField(default=0)  # 0=未评分

    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'movie_id')
        ordering = ['-update_time']