from django.urls import path,include,re_path
from verification import views
urlpatterns = [
    re_path(r'^emailcode/(?P<email>[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,})/$', views.EmailCodeView.as_view()),
]