import django_redis
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.views import View

from utils import response_code
from verification.emailCode.EmailSendCode import EmailVerifier


class EmailCodeView(View):
    '''
    邮箱验证码
    '''

    # 先检验request图片验证码是否正确

    # '/sms_code/' + this.email + '/?uuid=' + this.uuid + '&image_code=' + this.image_code;
    def get(self, request, email):
        # 先检验url参数是否齐全
        print(f"后端获取axios请求参数email为：{email}")
        # uuid = request.GET.get('uuid')
        # image_code = request.GET.get('image_code')
        # if not all([uuid, image_code]):
        #     print("email请求url参数不全")
        #     return HttpResponseForbidden('请求url中参数不全')
        # 再检验redis中的数据是否过期
        # redis_conn = django_redis.get_redis_connection('verification')

        '''
        JsonResponse说明
           JsonResponse(
            data,
            encoder='django.core.serializers.json.DjangoJSONEncoder',
            safe=True,
            json_dumps_params=None,
            **kwargs)
            data（必选）
            作用：需要序列化的数据对象
            特殊规则：
            当
            safe = True（默认）时，必须为字典类型
            允许嵌套数据类型：list, dict, str, int, float, bool, None

        '''
        # 发送邮箱验证码

        # 创建邮件验证器
        email_verifier = EmailVerifier()
        # 发送邮件并保存到redis中
        email_verifier.send_verification_code(email)
        print(email_verifier)
        print(email)

        return JsonResponse({
            'code': response_code.RETCODE.OK,
            'errmsg': '邮箱验证码发送成功'
        })
