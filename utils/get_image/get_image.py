import os
import json

from django.conf import settings

CACHE_FILE_PATH = os.path.join(settings.BASE_DIR, 'image_path_cache.json')

# 启动时一次性加载并排序图片列表，避免每次 os.listdir() 扫描
IMAGE_DIR = os.path.join(settings.BASE_DIR, 'static', 'image')
THUMB_DIR = os.path.join(settings.BASE_DIR, 'static', 'thumbnails')

_image_files = []
if os.path.isdir(IMAGE_DIR):
    _image_files = sorted([
        f for f in os.listdir(IMAGE_DIR)
        if os.path.isfile(os.path.join(IMAGE_DIR, f))
    ])
_image_count = len(_image_files)

# 内存缓存: movie_id -> filename (仅文件名，非完整路径)
_image_path_cache = {}
_write_counter = 0
_WRITE_INTERVAL = 50  # 每 50 条新命中才写一次磁盘


def _load_cache_from_disk():
    """加载旧缓存，兼容旧格式（从完整路径中提取文件名）"""
    cache = {}
    try:
        with open(CACHE_FILE_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        for movie_id_str, old_path in raw.items():
            try:
                mid = int(movie_id_str)
            except ValueError:
                continue
            filename = os.path.basename(old_path)
            if filename in _image_files or os.path.isfile(os.path.join(IMAGE_DIR, filename)):
                cache[mid] = filename
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return cache


_image_path_cache = _load_cache_from_disk()


def get_image_filename_by_movie_id(movie_id):
    """
    根据电影 ID 返回对应的图片文件名（仅文件名，如 '10144-The Little Mermaid.jpg'）。
    若目录为空或不存在，返回 None。
    """
    global _image_path_cache, _write_counter

    if movie_id in _image_path_cache:
        return _image_path_cache[movie_id]

    if _image_count == 0:
        return None

    index = movie_id % _image_count
    filename = _image_files[index]
    _image_path_cache[movie_id] = filename

    _write_counter += 1
    if _write_counter >= _WRITE_INTERVAL:
        _write_counter = 0
        try:
            with open(CACHE_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(_image_path_cache, f, ensure_ascii=False)
        except IOError:
            pass

    return filename


def get_image_url(movie_id, use_thumbnail=False):
    """
    返回完整的静态资源 URL。

    参数:
        movie_id: 电影 ID
        use_thumbnail: True 返回缩略图路径，False 返回原图路径

    返回:
        str: 如 '/static/image/10144-The Little Mermaid.jpg'
             或 '/static/thumbnails/10144-The Little Mermaid.jpg'
    """
    filename = get_image_filename_by_movie_id(movie_id)
    if not filename:
        return ''
    folder = 'thumbnails' if use_thumbnail else 'image'
    return f'/static/{folder}/{filename}'


# 保留旧函数名兼容（不推荐使用，返回仅文件名）
def get_image_path_by_movie_id(movie_id, directory_path=None):
    """已废弃，请使用 get_image_url()。保留以兼容旧代码。"""
    return get_image_filename_by_movie_id(movie_id)
