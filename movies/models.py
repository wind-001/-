from django.db import models

class Movie(models.Model):
    """电影模型类，对应 JSON 中的电影数据"""
    # 电影ID，作为主键（与JSON中的movie_id一致）
    movie_id = models.IntegerField(primary_key=True, verbose_name="电影ID")
    # 电影标题
    title = models.CharField(max_length=255, verbose_name="电影标题")
    # 上映年份
    year = models.IntegerField(verbose_name="上映年份")
    # 电影类型（逗号分隔的字符串，如 "Animation,Children's,Comedy"）
    # 如果使用PostgreSQL数据库，可替换为 ArrayField(models.CharField(max_length=50), blank=True)
    genres = models.CharField(max_length=255, verbose_name="电影类型")
    avg_rating = models.FloatField(default=0.0, null=True, blank=True, verbose_name="平均评分")
    class Meta:
        # 数据库表名
        db_table = "movies"
        # 后台显示的名称
        verbose_name = "电影"
        verbose_name_plural = "电影"
        # 默认按年份降序、标题升序排序
        ordering = ["-year", "title"]

    def __str__(self):
        """返回电影的完整标题（模仿JSON中的full_title）"""
        return f"{self.title} ({self.year})"

    @property
    def full_title(self):
        """模拟JSON中的full_title字段，动态生成"""
        return self.__str__()

    @property
    def genres_list(self):
        """将genres字符串转换为列表（还原JSON中的genres数组）"""
        if self.genres:
            return [genre.strip() for genre in self.genres.split(",")]
        return []