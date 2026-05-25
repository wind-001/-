import time

from django.utils.http import http_date


class StaticCacheMiddleware:
    """为开发环境的静态资源添加 Cache-Control 响应头"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path

        if path.startswith('/static/'):
            if path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico')):
                max_age = 86400  # 图片缓存 1 天
                response['Cache-Control'] = f'public, max-age={max_age}, immutable'
                response['Expires'] = http_date(time.time() + max_age)
            elif path.endswith(('.css', '.js')):
                response['Cache-Control'] = 'public, max-age=3600'

        return response
