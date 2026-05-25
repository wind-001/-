import json
import random

from django.contrib import auth
from django.shortcuts import render, redirect
from django_redis import get_redis_connection
from user.models import User, UserProfile
from django.views import View
from django.contrib.auth.models import User



class RegisterView(View):
    '''
    注册
    '''

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        print("开始 注册")
        # register_form = RegisterForm(request.POST)
        # print("校验完成")
        # print(register_form.errors)
        # if register_form.is_valid():
        #     print("校验无误")
        username = request.POST.get('username')
        password = request.POST.get('password')
        verifyCode = request.POST.get('verifyCode')
        email = request.POST.get('email')
        conn = get_redis_connection('verification')
        print(f"前端信息: username={username}  password={password}  verifyCode={verifyCode} email={email}")
        # if not email:
        mess_email = conn.get(email)
        if mess_email is None:
            print("过期")
            return render(request, 'login.html', {'error_msg': '邮箱验证码已过期'})
        if mess_email.decode() != verifyCode:
            print("验证码错误!!!")
            return render(request, 'register.html', {'error_msg': '邮箱验证码错误'})
            # # 若验证码没有问题，检查数据库中是否存在该用户
        if User.objects.filter(username=username).exists():
            print(f"{username} 用户已存在")
            return render(request, 'login.html', {'error_msg': '用户已存在'})
        # 若不存在，直接创建用户
        user = User.objects.create_user(username=username, password=password, email=email)
        print(f"{username}用户 注册成功")

        # Feature 5: 注册时即分配 A/B 实验分组
        UserProfile.objects.create(
            user=user,
            rec_group=random.choice(['A', 'B']),
        )
        print(f"{username} 分配至实验组: {user.userprofile.rec_group}")

        return redirect("login")
        # else:
        #     print("校验有误")
        #     context = register_form.errors
        #     return render(request, 'login.html', context=context)


class CollectPreferenceView(View):

    def post(self, request):

        if not request.user.is_authenticated:
            print("未登录401")
            return JsonResponse({'error': '未登录'}, status=401)

        try:
            data = json.loads(request.body)

            genres = data.get('genres', [])
            min_rating = data.get('minRating', 3.0)
            user_level = data.get('userLevel', 'new')

        except Exception:
            print("数据格式错误")
            return JsonResponse({'error': '数据格式错误'}, status=400)

        # 获取或创建用户Profile
        profile, created = UserProfile.objects.get_or_create(
            user=request.user
        )

        # 保存数据
        profile.preferred_genres = genres
        profile.min_rating = min_rating
        profile.user_level = user_level
        profile.cold_start_completed = True
        profile.save()

        return JsonResponse({
            'status': 'success',
            'message': '偏好设置已保存',
            'redirect_url': '/index/'  # 如果需要跳转，可以传一个 URL 给前端
        }, status=200)

class LoginView(View):
    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        print("开始 登录")
        # login_form = LoginForm(request.POST)
        # if login_form.is_valid():
        print("校验成功")
        username = request.POST.get('username')
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')
        print(f"username={username}  password={password} remembered={remembered} 正在尝试登录...")
        # 这里增加功能,希望用户使用邮箱也能够登录,因此需要重写authenticate方法
        # 创建一个文件,然后创建一个类继承ModelBackend,在里面重写authenticate方法即可
        user = auth.authenticate(username=username, password=password)
        print(f"该用户是{user}")
        if user is None:
            # 区分用户不存在还是密码错误
            if User.objects.filter(username=username).exists():
                return render(request, 'login.html', {'error_msg': '密码错误，请重试'})
            else:
                return render(request, 'login.html', {'error_msg': '用户名不存在'})
        if not user.is_active:
            return render(request, 'login.html', {'error_msg': '该账号已被禁用，请联系管理员'})

        # 状态保持
        print("开始 状态保持")
        auth.login(request, user)
        print("状态保持完成")
        if remembered:
            # 默认保存14天
            request.session.set_expiry(None)
        else:
            request.session.set_expiry(0)
        print("准备返回")
        next = request.GET.get('next')
        print(f"next = {next}")
        if next:
            response = redirect(next)
            print(next)
        # 是否第一次登录
        userProfle,created = UserProfile.objects.get_or_create(user_id=request.user.id)

        # Feature 5: A/B 分组 - 兼容旧用户未分配分组的情况
        if not userProfle.rec_group or userProfle.rec_group not in ('A', 'B'):
            userProfle.rec_group = random.choice(['A', 'B'])
            userProfle.save()
            print(f"{request.user.username} 分配至实验组: {userProfle.rec_group}")

        if not userProfle.cold_start_completed:
            return render(request, 'collect.html', status=200)

        # response = render(request, 'index.html', status=200)
        response = redirect('index')
        response.set_cookie('username', request.user.username, 3600)
        print("返回完成")
        return response
    # else:
    #     print("校验有误")
    #     context = login_form.errors
    #     return render(request, 'login.html', context={'forms.errmsg': context})


class LogoutView(View):
    def get(self, request):
        # 清除session
        auth.logout(request)
        response = redirect("index")
        response.delete_cookie('username')
        return response


from django.views import View
from django.contrib.auth import get_user_model, logout  # 导入 logout
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin


User = get_user_model()
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
from user.models import UserProfile  # 按你的实际路径

User = get_user_model()


class UpdateProfileView(LoginRequiredMixin, View):

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        user = request.user

        if not action:
            return JsonResponse({'status': 'error', 'message': '缺少 action 参数'})

        # ===============================
        # A. 安全设置（改名 / 改密码）
        # ===============================
        if action == 'security':
            return self.handle_security(request, user)

        # ===============================
        # B. 个性化推荐设置
        # ===============================
        elif action == 'preference':
            return self.handle_preference(request, user)

        return JsonResponse({'status': 'error', 'message': '无效操作'})

    # ===============================
    # 安全设置逻辑
    # ===============================
    def handle_security(self, request, user):
        new_username = request.POST.get('username', '').strip()
        old_pw = request.POST.get('old_password')
        new_pw = request.POST.get('new_password', '').strip()

        # 校验旧密码
        if not user.check_password(old_pw):
            return JsonResponse({'status': 'error', 'message': '当前密码验证错误'})

        # 修改用户名
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exclude(id=user.id).exists():
                return JsonResponse({'status': 'error', 'message': '该昵称已存在'})
            user.username = new_username

        # 修改密码
        if new_pw:
            if len(new_pw) < 6:
                return JsonResponse({'status': 'error', 'message': '新密码至少6位'})
            user.set_password(new_pw)
            user.save()
            logout(request)
            return JsonResponse({'status': 'success', 'need_login': True})

        user.save()
        return JsonResponse({'status': 'success', 'need_login': False})

    # ===============================
    # 个性化设置逻辑
    # ===============================
    def handle_preference(self, request, user):
        try:
            profile, _ = UserProfile.objects.get_or_create(user=user)

            def get_bool(field):
                return request.POST.get(field) in ['on', 'true', '1']

            is_explore = get_bool('is_explore')
            is_monday_push = get_bool('is_monday_push') or get_bool('monday_push')

            profile.is_explore = is_explore
            profile.is_monday_push = is_monday_push

            if is_monday_push:
                profile.is_send = True

            # Save preferred genres from multi-select
            preferred_genres_cn = []
            genres_raw = request.POST.getlist('preferred_genres')
            if genres_raw:
                from utils.genres import Genres
                valid_genres = [g for g in genres_raw if g in Genres.GENRE_MAP]
                profile.preferred_genres = valid_genres
                preferred_genres_cn = [Genres.GENRE_MAP.get(g, g) for g in valid_genres]

            profile.save(update_fields=[
                'is_explore',
                'is_monday_push',
                'is_send',
                'preferred_genres'
            ])

            return JsonResponse({
                'status': 'success',
                'data': {
                    'is_explore': profile.is_explore,
                    'is_monday_push': profile.is_monday_push,
                    'preferred_genres_cn': preferred_genres_cn,
                },
                'message': '个性化偏好已更新'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'更新失败: {str(e)}'
            })
