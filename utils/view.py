from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import  JsonResponse
from utils.response_code import RETCODE



class LoginRequireJsonMixin(LoginRequiredMixin):
    def handle_no_permission(self):
        return JsonResponse({"code":RETCODE.SESSIONERR,'errmsg':"用户未登录"})
