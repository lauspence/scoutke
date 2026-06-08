from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('talent-radar/', views.talent_radar, name='talent_radar'),
    path('club/dashboard/', views.club_dashboard, name='club_dashboard'),
]
