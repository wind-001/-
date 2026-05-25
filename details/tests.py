import os
import random

from django.conf import settings


class DetailView():
    # def get(self, request, movie_id):
    #     # movie = Movie.objects.get(movie_id=movie_id)
    #     movie = {
    #         'id': movie.movie_id,
    #         'title': movie.title,
    #         'year': movie.year,
    #         'genre': movie.genres,
    #         'rating': round(random.random() + 9, 1),
    #         'poster_url': 'https://example.com/interstellar.jpg',
    #         'description': '近未来的地球黄沙遍野，小麦、秋葵等基础农作物相继因枯萎病灭绝，人类不再像从前那样仰望星空，放纵想象力和灵感的迸发，而是每日在沙尘暴的肆虐下倒数着所剩不多的光景。在家务农的前NASA宇航员库珀接连在女儿墨菲的房间发现了奇异磁场，在神秘力量的指引下，他和一众伙伴踏上了穿越星际的旅程，寻找人类新的家园。'
    #     }
    #     return render(request, 'details.html', {'movie': movie})

    def get_random_filename_from_dir(directory_path=r'../static/image'):
        """
        从指定目录中随机获取一个文件名（包含文件后缀）

        参数:
            directory_path (str): 目标目录的路径（绝对路径/相对路径均可）

        返回:
            str: 随机选中的文件名；若目录为空/不存在，返回 None
        """
        # 步骤1：校验目录是否存在
        if not os.path.isdir(directory_path):
            print(f"错误：目录 '{directory_path}' 不存在！")
            return None

        # 步骤2：获取目录下所有文件（排除子目录）
        file_list = []
        for filename in os.listdir(directory_path):
            # 拼接文件完整路径，判断是否为文件（非目录）
            file_full_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_full_path):
                file_list.append(filename)

        # 步骤3：判断文件列表是否为空
        if not file_list:
            print(f"提示：目录 '{directory_path}' 下无文件！")
            return None

        # 步骤4：随机选择一个文件
        random_file = random.choice(file_list)
        return random_file


if __name__ == "__main__":
    # 替换为你要指定的目录路径（示例：Windows 路径/ macOS/Linux 路径）
    # target_dir = r"C:\Users\YourName\Pictures\movie_posters"  # Windows 路径（r 避免转义）
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MoviesRec.settings')
    result = DetailView.get_random_filename_from_dir()
    print(os.path.join(settings.BASE_DIR, 'static', 'image'))
    # 输出结果
    if result:
        print(f"随机选中的文件：{result}")