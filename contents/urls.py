from django.urls import path,include
from contents import views
urlpatterns = [
    #    path('admin/', admin.site.urls),
    path('',views.IndexView.as_view(),name = "index"),
    path('index/',views.IndexView.as_view(),name = "index"),
    path('category/',views.CategoryView.as_view(),name = "category"),
    path('category/<str:genres>/',views.CategoryView.as_view()),
    path('rank/',views.RankView.as_view(),name='rank'),

    path('search/<str:movies_name>/',views.SearchView.as_view()),
    path('profile/',views.ProfileView.as_view(),name = "profile"),
    path("sendinfo/",views.SendInfoView.as_view(),name='sendinfo'),
    path("expstats/", views.ExpStatsView.as_view(), name='expstats'),
]
