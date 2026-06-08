from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.scout_dashboard, name='scout_dashboard'),
    path("search/", views.scout_search, name="scout_search"),
    path("saved/", views.saved_players, name="saved_players"),
    path("save/<int:player_id>/", views.save_player, name="save_player"),
    path("unsave/<int:player_id>/", views.unsave_player, name="unsave_player"),
    path("insights/", views.scout_insights, name="scout_insights"),
    path("repost/<int:post_id>/", views.repost_post, name="repost"),
    path('profile/edit/', views.edit_scout_profile, name='edit_scout_profile'),
    path("delete-post/<int:post_id>/", views.delete_post, name="delete_post"),


]
