from django.urls import path,include
from user import views
urlpatterns = [

    path('register/', views.RegisterView.as_view(), name='register'),
    path('collect/', views.CollectPreferenceView.as_view(),name='collect'),
    path('login/', views.LoginView.as_view(), name='login'),

    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('update_profile/', views.UpdateProfileView.as_view(), name='update_profile'),

]