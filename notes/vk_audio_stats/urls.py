from django.conf.urls import include
from django.urls import path

from . import views


app_name = 'vk_audio_stats'
urlpatterns = [
    path('', views.index, name='index'),
    path('genre/', views.genre, name='genre'),
    path('user/<int:vk_id>', views.UserView.as_view(), name='user')
]
