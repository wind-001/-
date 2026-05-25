import os
import django
import torch
import numpy as np
import pandas as pd
import torch.nn as nn
import json
import redis
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm

# ==========================
# 1. 环境与 Redis 初始化
# ==========================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MoviesRec.settings")
django.setup()

from ratings.models import Rating

r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ==========================
# 2. 极速数据预处理 (ORM 优化)
# ==========================
def load_data_fast():
    print("🚀 正在从数据库提取数据 (使用 Values 优化)...")
    # .values() 避开 Django Model 实例包装，百万数据读取仅需几秒
    queryset = Rating.objects.all().values("user_id", "movie_id", "rating")
    df = pd.DataFrame(list(queryset))

    # 显式转隐式
    df = df[df["rating"] >= 4].copy()

    # 快速 ID 映射
    user_map = {u: i for i, u in enumerate(df["user_id"].unique())}
    item_map = {m: i for i, m in enumerate(df["movie_id"].unique())}

    df["u_idx"] = df["user_id"].map(user_map).astype(np.int32)
    df["i_idx"] = df["movie_id"].map(item_map).astype(np.int32)

    # 构造正样本哈希表，用于快速负采样
    user_pos = df.groupby("u_idx")["i_idx"].apply(set).to_dict()

    return df[["u_idx", "i_idx"]].values, user_pos, len(user_map), len(item_map), user_map, item_map


# ==========================
# 3. 预采样 Dataset (消除训练中的 While 循环)
# ==========================
class FastNCFDataset(Dataset):
    def __init__(self, pos_pairs, user_pos, num_items, num_neg=4):
        self.pos_pairs = pos_pairs
        self.user_pos = user_pos
        self.num_items = num_items
        self.num_neg = num_neg
        self.refresh()  # 初始执行一次采样

    def refresh(self):
        """每轮 Epoch 前批量生成负样本，不在 __getitem__ 里做随机循环"""
        print("🔄 正在批量生成负样本...")
        u_list, i_list, l_list = [], [], []
        for u, i in self.pos_pairs:
            # 正样本
            u_list.append(u);
            i_list.append(i);
            l_list.append(1.0)
            # 负样本
            for _ in range(self.num_neg):
                neg = np.random.randint(0, self.num_items)
                while neg in self.user_pos[u]:
                    neg = np.random.randint(0, self.num_items)
                u_list.append(u);
                i_list.append(neg);
                l_list.append(0.0)

        self.users = torch.tensor(u_list, dtype=torch.long)
        self.items = torch.tensor(i_list, dtype=torch.long)
        self.labels = torch.tensor(l_list, dtype=torch.float)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.users[idx], self.items[idx], self.labels[idx]


# ==========================
# 4. NCF 模型定义
# ==========================
class NCF(nn.Module):
    def __init__(self, num_users, num_items, embed_dim=32):
        super().__init__()
        self.user_gmf = nn.Embedding(num_users, embed_dim)
        self.item_gmf = nn.Embedding(num_items, embed_dim)
        self.user_mlp = nn.Embedding(num_users, embed_dim)
        self.item_mlp = nn.Embedding(num_items, embed_dim)

        self.mlp = nn.Sequential(
            nn.Linear(embed_dim * 2, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        self.output = nn.Linear(embed_dim + 32, 1)

    def forward(self, user, item):
        gmf = self.user_gmf(user) * self.item_gmf(item)
        mlp = self.mlp(torch.cat([self.user_mlp(user), self.item_mlp(item)], dim=-1))
        return torch.sigmoid(self.output(torch.cat([gmf, mlp], dim=-1)))


# ==========================
# 5. 提速版训练主逻辑
# ==========================
def train_fast(epochs=10, batch_size=4096):
    # 1. 加载数据
    pos_pairs, user_pos, num_users, num_items, user_map, item_map = load_data_fast()

    dataset = FastNCFDataset(pos_pairs, user_pos, num_items)
    # num_workers 开启多线程，pin_memory 加速数据向 GPU 拷贝
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True,
                        num_workers=4, pin_memory=True)

    model = NCF(num_users, num_items).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()

    # 启用自动混合精度 (AMP)，RTX 显卡提速神器
    scaler = torch.cuda.amp.GradScaler()

    print(f"🔥 开始训练 | 设备: {device} | 样本量: {len(dataset)}")

    for epoch in range(epochs):
        model.train()
        dataset.refresh()  # 每轮刷新负样本，增加模型鲁棒性

        total_loss = 0
        pbar = tqdm(loader, desc=f"Epoch {epoch + 1}")

        for u, i, l in pbar:
            u, i, l = u.to(device, non_blocking=True), i.to(device, non_blocking=True), l.to(device, non_blocking=True)

            optimizer.zero_grad(set_to_none=True)  # 比 zero_grad() 更快

            # AMP 混合精度训练
            with torch.cuda.amp.autocast():
                pred = model(u, i).squeeze()
                loss = criterion(pred, l)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            total_loss += loss.item()
            pbar.set_postfix(loss=f"{loss.item():.4f}")

    # 导出实时系统所需的 Embedding 和映射表
    print("💾 正在保存生产级权重...")
    torch.save({
        "item_embs": model.item_mlp.weight.data.cpu().numpy(),
        "item_map": item_map,
        "user_map": user_map
    }, "ncf_production.pth")
    print("✅ 训练完成，模型已上线！")


if __name__ == "__main__":
    train_fast()
    # current_dir = os.path.abspath(__file__)
    # print(os.path.dirname(current_dir))