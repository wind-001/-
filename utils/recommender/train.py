import os
import django
import torch
import random
import pandas as pd
import numpy as np
import torch.nn as nn

# ==============================
# Django 初始化
# ==============================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MoviesRec.settings")
django.setup()

from ratings.models import Rating

# ==============================
# 设备
# ==============================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# ==============================
# 1️⃣ 读取数据 + 显式转隐式 + ID重映射
# ==============================
def load_data():
    ratings = Rating.objects.all().values("user_id", "movie_id", "rating")
    print(ratings)
    df = pd.DataFrame(list(ratings))
    print(f"df = {df}")
    # 显式 → 隐式
    df = df[df["rating"] >= 4]
    df["label"] = 1
    # print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    # print(f"df = {df}")

    # 用户ID映射
    unique_users = df["user_id"].unique()
    user_map = {uid: idx for idx, uid in enumerate(unique_users)}

    # 电影ID映射
    unique_items = df["movie_id"].unique()
    item_map = {mid: idx for idx, mid in enumerate(unique_items)}

    df["user"] = df["user_id"].map(user_map)
    df["item"] = df["movie_id"].map(item_map)

    print("用户数:", len(user_map))
    print("电影数:", len(item_map))
    # print('load退出前xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
    # print(f'df = {df}')
    # print(f'user_map = {user_map}')
    # print(f'item_map = {item_map}')

    return df, user_map, item_map


# ==============================
# 2️⃣ 负采样
# ==============================
def negative_sampling(df, num_items, num_neg=4):
    user_pos = df.groupby("user")["item"].apply(set).to_dict()
    '''
    user_pos:
         {
     用户0: {电影1, 电影5, 电影9},
     用户1: {电影2, 电影3},
     用户2: {电影0, 电影6, 电影7, 电影8},
     ...
         }'''
    samples = []

    for user in user_pos:
        pos_items = user_pos[user]

        # 电影编号集合,存储当前用户的正样本

        for item in pos_items:
            samples.append([user, item, 1])
            # 存储所有的正样本
            print(samples)
            # 构造与该正样本对应的 num_neg 个负样本    1-4__1-10
            for _ in range(num_neg):
                neg_item = random.randint(0, num_items - 1)
                while neg_item in pos_items:
                    neg_item = random.randint(0, num_items - 1)

                samples.append([user, neg_item, 0])

    return pd.DataFrame(samples, columns=["user", "item", "label"])


# ==============================
# 3️⃣ NCF模型
# ==============================
class NCF(nn.Module):
    def __init__(self, num_users, num_items, embed_dim=32):
        super(NCF, self).__init__()

        # GMF
        self.user_gmf = nn.Embedding(num_users, embed_dim)
        self.item_gmf = nn.Embedding(num_items, embed_dim)

        # MLP
        self.user_mlp = nn.Embedding(num_users, embed_dim)
        self.item_mlp = nn.Embedding(num_items, embed_dim)

        self.mlp = nn.Sequential(
            nn.Linear(embed_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
        )

        self.output = nn.Linear(embed_dim + 32, 1)

    def forward(self, user, item):
        # GMF
        gmf_user = self.user_gmf(user)
        gmf_item = self.item_gmf(item)
        gmf_out = gmf_user * gmf_item

        # MLP
        mlp_user = self.user_mlp(user)
        mlp_item = self.item_mlp(item)
        mlp_out = self.mlp(torch.cat([mlp_user, mlp_item], dim=-1))

        # 拼接
        concat = torch.cat([gmf_out, mlp_out], dim=-1)
        out = self.output(concat)

        return torch.sigmoid(out)


# ==============================
# 4️⃣ 训练函数
# ==============================
def train(epochs=10, batch_size=512, lr=0.001):

    print("开始加载数据...")
    df, user_map, item_map = load_data()

    num_users = len(user_map)
    num_items = len(item_map)

    print("开始负采样...")
    df_train = negative_sampling(df, num_items)
    # columns = ["user", "item", "label"]

    users = torch.LongTensor(df_train["user"].values).to(device)
    items = torch.LongTensor(df_train["item"].values).to(device)
    labels = torch.FloatTensor(df_train["label"].values).to(device)

    dataset = torch.utils.data.TensorDataset(users, items, labels)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = NCF(num_users, num_items).to(device)

    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    print("开始训练...")

    for epoch in range(epochs):
        model.train()  # 设置模型为训练模式（启用Dropout等）
        total_loss = 0  # 记录本轮总损失

        # 遍历每个批次的数据
        for u, i, l in loader:
            optimizer.zero_grad()  # 清空梯度（避免累积）

            # 前向传播：输入用户和电影索引，得到预测概率
            preds = model(u, i).squeeze()  # 挤压维度：(batch_size,1) → (batch_size,)
            # 计算损失：预测值与真实标签的差异
            loss = criterion(preds, l)

            # 反向传播：计算梯度
            loss.backward()
            # 梯度下降：更新模型参数
            optimizer.step()

            # 累加损失
            total_loss += loss.item()

        # 打印本轮训练损失（用于监控训练过程）
        print(f"Epoch {epoch + 1}/{epochs}  Loss: {total_loss:.4f}")

    # ==============================
    # 保存模型 + 映射
    # ==============================
    torch.save({
        "model_state_dict": model.state_dict(),
        "user_map": user_map,
        "item_map": item_map,
        "num_users": num_users,
        "num_items": num_items
    }, "ncf_model.pth")
    """
    '''
model_state_dict 
{
    "user_gmf.weight": tensor([[...]]),  # GMF用户嵌入层权重
    "item_gmf.weight": tensor([[...]]),  # GMF电影嵌入层权重
    "user_mlp.weight": tensor([[...]]),  # MLP用户嵌入层权重
    "item_mlp.weight": tensor([[...]]),  # MLP电影嵌入层权重
    "mlp.0.weight": tensor([[...]]),     # MLP第一层全连接层权重
    "mlp.0.bias": tensor([...]),         # MLP第一层全连接层偏置
    "mlp.3.weight": tensor([[...]]),     # MLP第二层全连接层权重
    "mlp.3.bias": tensor([...]),         # MLP第二层全连接层偏置
    "output.weight": tensor([[...]]),    # 输出层权重
    "output.bias": tensor([...])         # 输出层偏置
}
'''
    """
    """
    user_map:
    user_map = {
    1001: 0,   # 原始用户ID 1001 → 模型索引 0
    1002: 1,   # 原始用户ID 1002 → 模型索引 1
    ...
}
 item_map:
item_map = {
    2001: 0,   # 原始电影ID 2001 → 模型索引 0
    2002: 1,   # 原始电影ID 2002 → 模型索引 1
    ...
}
    """
    print("模型训练完成，已保存为 ncf_model.pth")


# ==============================
# 主函数
# ==============================
if __name__ == "__main__":
    train()