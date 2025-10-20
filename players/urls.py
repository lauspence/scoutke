from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.player_dashboard, name='dashboard'),
    path("profile/update/", views.update_profile, name="update_profile"),
    path('profile/<int:user_id>/', views.view_profile, name='view_profile'),
    path('followers/<int:user_id>/', views.followers_list, name='followers_list'),
    path('following/<int:user_id>/', views.following_list, name='following_list'),
    path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
   
]
