"""一次性脚本：为 static/image/ 下所有海报生成 200x300 缩略图到 static/thumbnails/"""
import os
import sys
from pathlib import Path

from PIL import Image

THUMBNAIL_SIZE = (200, 300)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
IMAGE_DIR = BASE_DIR / 'static' / 'image'
THUMB_DIR = BASE_DIR / 'static' / 'thumbnails'


def generate_all_thumbnails():
    os.makedirs(THUMB_DIR, exist_ok=True)

    exts = {'.jpg', '.jpeg', '.png'}
    image_files = [f for f in os.listdir(IMAGE_DIR)
                   if os.path.isfile(os.path.join(IMAGE_DIR, f))
                   and os.path.splitext(f)[1].lower() in exts]

    generated = 0
    for filename in image_files:
        src = os.path.join(IMAGE_DIR, filename)
        dst = os.path.join(THUMB_DIR, filename)

        if os.path.exists(dst):
            continue

        try:
            with Image.open(src) as img:
                img = img.convert('RGB')
                img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                img.save(dst, 'JPEG', quality=80, optimize=True)
            generated += 1
        except Exception as e:
            print(f"Failed: {filename}: {e}")

    print(f"Generated {generated} thumbnails in {THUMB_DIR}")


if __name__ == '__main__':
    sys.path.insert(0, str(BASE_DIR))
    generate_all_thumbnails()
