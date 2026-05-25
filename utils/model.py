from django.db import models


class BaseModel(models.Model):
    # 创建时间
    create_time = models.DateTimeField(auto_now_add=True)
    # 更新时间
    update_time = models.DateTimeField(auto_now=True)

    class Meta:
        # 让模型类在迁移同步过程中不单独创建一张表
        abstract = True