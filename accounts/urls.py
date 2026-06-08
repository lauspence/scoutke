from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings_view, name='settings'),
    path('verification/', views.request_verification, name='request_verification'),
    path('verification/queue/', views.verification_queue, name='verification_queue'),
    path('verification/<int:request_id>/<str:action>/', views.review_verification_request, name='review_verification_request'),
]
