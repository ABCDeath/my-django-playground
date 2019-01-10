from django.conf.urls import include
from django.urls import path

from . import views


app_name = 'vk_audio_stats'
urlpatterns = [
    path('', views.index, name='index'),
]
