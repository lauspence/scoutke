from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('club/dashboard/', views.club_dashboard, name='club_dashboard'),
]
