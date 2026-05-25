
# from django.contrib import admin
from django.urls import path,re_path
from details import views
urlpatterns = [
    re_path(r'detail/(?P<movie_id>\d+)',views.DetailView.as_view(),name='detail'),
    path('collection/',views.CollectionView.as_view()),
    path("rate_movie/", views.RateMovieView.as_view(), name="rate_movie"),

]
