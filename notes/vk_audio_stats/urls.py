from django.conf.urls import include
from django.urls import path

from . import views


app_name = 'vk_audio_stats'
urlpatterns = [
    path('genre/', views.genre, name='genre'),
    path('user/<int:pk>', views.UserView.as_view(), name='user')
]
