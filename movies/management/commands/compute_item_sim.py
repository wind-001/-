"""
Feature 2: 离线计算电影 Item Embedding 之间的余弦相似度矩阵
用法: python manage.py compute_item_sim
"""
import json
import os
import numpy as np
import torch
from django.core.management.base import BaseCommand
from django.db import connection
from movies.models import Movie


class Command(BaseCommand):
    help = '基于 NCF item embedding 计算电影相似度并存入数据库'

    def handle(self, *args, **options):
        self.stdout.write('开始计算电影相似度...')

        BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        ))), 'utils', 'recommender')
        MODEL_PATH = os.path.join(BASE_DIR, "ncf_production.pth")

        if not os.path.exists(MODEL_PATH):
            self.stderr.write(f'模型文件不存在: {MODEL_PATH}')
            return

        checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=False)
        item_embs = checkpoint["item_embs"].numpy()
        item_map = checkpoint["item_map"]
        rev_item_map = {v: k for k, v in item_map.items()}

        self.stdout.write(f'Item embeddings shape: {item_embs.shape}')
        self.stdout.write(f'Total items in model: {len(item_map)}')

        # 归一化
        norm = item_embs / (np.linalg.norm(item_embs, axis=1, keepdims=True) + 1e-9)

        # 创建或清空表
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS movies_itemsim (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    movie_id INT NOT NULL,
                    sim_movie_id INT NOT NULL,
                    similarity FLOAT NOT NULL,
                    INDEX idx_movie_id (movie_id),
                    UNIQUE KEY unique_pair (movie_id, sim_movie_id)
                )
            """)
            cursor.execute("TRUNCATE TABLE movies_itemsim")
            self.stdout.write('相似度表已清空')

        # 获取数据库中存在的全部电影 ID
        db_movie_ids = set(Movie.objects.values_list('movie_id', flat=True))

        top_k = 20  # 每部电影保留 top-20 相似
        batch_size = 500
        insert_sql = "INSERT INTO movies_itemsim (movie_id, sim_movie_id, similarity) VALUES (%s, %s, %s)"

        all_ids = list(item_map.keys())
        total = len(all_ids)

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            batch_ids = all_ids[start:end]
            batch_indices = [item_map[mid] for mid in batch_ids]
            batch_embs = norm[batch_indices]

            # 余弦相似度：batch × all
            scores = np.dot(batch_embs, norm.T)

            rows = []
            for i, mid in enumerate(batch_ids):
                if mid not in db_movie_ids:
                    continue
                row_scores = scores[i]
                # 排除自身
                row_scores[item_map[mid]] = -1
                # 取 top_k
                top_indices = row_scores.argsort()[-top_k:][::-1]
                for j in top_indices:
                    sim_mid = rev_item_map[j]
                    if sim_mid not in db_movie_ids:
                        continue
                    sim_score = float(row_scores[j])
                    if sim_score > 0:
                        rows.append((mid, sim_mid, sim_score))

                if len(rows) >= 500:
                    with connection.cursor() as cursor:
                        cursor.executemany(insert_sql, rows)
                    rows = []

            if rows:
                with connection.cursor() as cursor:
                    cursor.executemany(insert_sql, rows)

            self.stdout.write(f'  进度: {end}/{total} ({end*100//total}%)')

        self.stdout.write(self.style.SUCCESS('电影相似度计算完成！'))
