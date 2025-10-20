from django.urls import path
from . import views

urlpatterns = [
    path("", views.feed, name="feed"),
    path('like/<int:post_id>/', views.like_post, name='like_post'),
    path('comment/<int:post_id>/', views.add_comment, name='add_comment'),
    path("repost/<int:post_id>/", views.repost_post, name="repost_post"),
    path('fetch-new-posts/', views.fetch_new_posts, name='fetch_new_posts'),

]
