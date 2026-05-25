# MovieRec 电影推荐系统

基于 Django + PyTorch NCF 的电影推荐系统，支持冷启动偏好收集、个性化推荐、详情页相似影片、A/B 实验框架等功能。

---

## 目录结构

```
MoviesRec/
├── MoviesRec/            # Django 配置 (settings/urls/wsgi)
├── contents/             # 首页、分类、排行榜、搜索、个人中心
├── details/              # 电影详情页、收藏、评分
├── movies/               # 电影数据模型 & 物品相似度计算
├── movies_users/         # 用户-电影交互数据
├── ratings/              # 评分数据
├── user/                 # 用户模型、注册/登录、偏好更新
├── verification/         # 邮箱验证码发送
├── utils/
│   ├── recommender/      # NCF 推荐引擎 (PyTorch)
│   │   ├── recommend.py  # 推荐核心逻辑
│   │   ├── train.py      # 模型训练
│   │   └── ncf_production.pth  # 训练好的模型权重
│   ├── get_image/        # 电影海报图片获取
│   ├── model.py          # 基础模型
│   └── test.py           # TMDB 海报爬取脚本 (需自行创建，见下文)
├── static/
│   ├── css/              # 样式文件
│   └── image/            # 电影海报图片 (需自行下载)
├── templates/            # Django 模板
└── README.md
```

---

## 环境要求

| 组件 | 版本/说明 |
|---|---|
| Python | 3.8+ (开发使用 3.11) |
| MySQL | 5.7+ |
| Redis | 6.0+ |
| PyTorch | 2.0+ (CPU 版即可) |

### Python 依赖

```bash
pip install django==3.2 django-redis torch numpy requests aiohttp tqdm pymysql pillow
```

---

## 配置步骤

### 1. 克隆项目

```bash
git clone https://github.com/wind-001/-.git
cd MoviesRec
```

### 2. MySQL 数据库

创建数据库和用户：

```sql
CREATE DATABASE movies_rec DEFAULT CHARACTER SET utf8mb4;
-- 用户/密码需与 settings.py 中 DATABASES 配置一致，默认为 root/123456
```

在 `MoviesRec/settings.py` 中确认数据库配置：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'movies_rec',
        'USER': 'root',
        'PASSWORD': '123456',   # 改为你自己的密码
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

### 3. Redis

确保 Redis 服务运行在 `127.0.0.1:6379`。Windows 用户可下载 [Memurai](https://www.memurai.com/) 或使用 WSL 安装。

```bash
# Linux/Mac
redis-server

# Windows (Memurai)
memurai-server
```

### 4. 初始化数据

项目依赖 JSON 数据文件 (`movies.json`, `ratings.json`, `movies_users.json`, `image_path_cache.json`)。由于这些文件较大（总计约 178MB），未包含在 git 仓库中。

**你需要联系项目作者获取这些数据文件**，将它们放置在项目根目录后执行：

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata movies.json
python manage.py loaddata ratings.json
```

> 或者直接导入 MySQL dump 文件（如果有）。

### 5. 下载电影海报图片

创建 `utils/test.py` 文件，填入你自己的 TMDB API Key，然后运行爬取脚本：

```python
# utils/test.py (模板)
import os
import random
import asyncio
import requests
import traceback

TARGET_COUNT = 300
SAVE_DIR = "movie_posters"
TMDB_API_KEY = "你的TMDB_API_KEY"     # <--- 替换为你的 Key
TMDB_BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
GENRE_IDS = [28, 12, 16, 35, 80, 99, 18, 10751, 14, 36, 27, 10402, 9648, 10749, 878]
MAX_PAGE = 5000
EMPTY_PAGE_LIMIT = 10

PROXY_CONFIG = {
    "use_proxy": True,           # 国内需开代理
    "proxy_url": "http://127.0.0.1:7890"
}

def get_tmdb_api_key():
    if TMDB_API_KEY == "YOUR_API_KEY":
        print("请替换有效的 TMDB API Key！")
        exit(1)
    return TMDB_API_KEY

# ... (完整代码见原始文件或联系作者获取)
```

TMDB API Key 申请步骤：
1. 注册 [TMDB 账号](https://www.themoviedb.org/signup)
2. 进入 [API 设置页](https://www.themoviedb.org/settings/api)
3. 选择 "Developer"，填写用途说明，获取 API Key

运行爬取：

```bash
python utils/test.py
```

图片将下载到 `utils/movie_posters/` 目录，需将其移动到 `static/image/` 供前端展示。

### 6. 邮箱验证码配置

创建 `verification/emailCode/EmailSendCode.py`，填入你自己的 QQ 邮箱 SMTP 授权码：

```python
# verification/emailCode/EmailSendCode.py (模板)
import smtplib
from email.mime.text import MIMEText
import random


class EmailCode:
    def __init__(self):
        self.sender = '你的QQ邮箱@qq.com'      # <--- 替换
        self.password = 'QQ邮箱SMTP授权码'       # <--- 替换
        self.smtp_server = 'smtp.qq.com'
        self.port = 587
        self.receiver = None
        self.code = None

    def generate_code(self):
        self.code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return self.code

    def send_email(self, receiver):
        self.receiver = receiver
        msg = MIMEText(f'您的验证码是：{self.code}，5分钟内有效。', 'plain', 'utf-8')
        msg['Subject'] = 'MovieRec 邮箱验证码'
        msg['From'] = self.sender
        msg['To'] = receiver
        try:
            with smtplib.SMTP(self.smtp_server, self.port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, receiver, msg.as_string())
            return True
        except Exception as e:
            print(f'邮件发送失败: {e}')
            return False
```

同理创建 `verification/emailCode/EmailSendMovies.py`（电影周报推送），结构类似。

> QQ 邮箱 SMTP 授权码获取：QQ 邮箱 → 设置 → 账户 → POP3/SMTP 服务 → 开启并获取授权码

### 7. 启动项目

```bash
python manage.py runserver
```

访问 `http://127.0.0.1:8000`。

### 8. 启动定时任务（可选）

周报推送依赖 APScheduler，在主 URL 中已自动启动。若需独立运行：

```bash
python manage.py shell -c "from user.schedule import start_scheduler; start_scheduler()"
```

---

## 功能概览

| 功能 | 说明 |
|---|---|
| 首页推荐 | 混合推荐（热门 + NCF 个性化），含推荐理由 |
| 分类浏览 | 按 19 种电影类型筛选 |
| 排行榜 | 高分榜、热门榜、NCF 推荐榜 |
| 电影详情 | 影片信息、相似影片推荐、收藏、评分 |
| 冷启动 | 新用户首次登录选择偏好类型 |
| 用户画像 | 实时计算的观影偏好标签 |
| A/B 实验 | 对照组/实验组，Chart.js 可视化对比 |
| 邮箱推送 | 周一电影周报（需配置 SMTP） |

---

## 常见问题

**Q: 首页推荐为空？**
确保 `utils/recommender/ncf_production.pth` 模型文件存在，且 MySQL 中有电影数据。

**Q: 图片不显示？**
运行 `utils/test.py` 下载海报，将 `movie_posters/` 中的图片复制到 `static/image/`。

**Q: 注册时邮箱验证码收不到？**
检查 `verification/emailCode/EmailSendCode.py` 中的 SMTP 配置是否正确，QQ 邮箱需使用授权码而非登录密码。
