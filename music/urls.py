from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('discover/', views.discover, name='discover'),
    path('library/', views.library, name='library'),
    path('playlists/', views.playlists, name='playlists'),
    path('genres/', views.genres, name='genres'),
    path('genre/<int:genre_id>/', views.genre_songs, name='genre_songs'),
    path('play-song/<int:song_id>/', views.play_song, name='play_song'),
    path('like-song/<int:song_id>/', views.like_song, name='like_song'),
    path('download-song/<int:song_id>/', views.download_song, name='download_song'),
    path('search/', views.search, name='search'),
    path('analytics/song/<int:song_id>/', views.song_analytics, name='song_analytics'),
    path('analytics/top-songs/', views.top_songs, name='top_songs'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup, name='signup'),
    path('get-song-stats/<int:song_id>/', views.get_song_stats, name='get_song_stats'),
    path('upload/', views.upload_music, name='upload_music'),
    path('my-uploads/', views.my_uploads, name='my_uploads'),
]