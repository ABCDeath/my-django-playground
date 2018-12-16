from django.db import models


class AudioStatsDBRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'vk_audio_stats':
            return 'audios_db'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'vk_audio_stats':
            return 'audios_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (obj1._meta.app_label == 'vk_audio_stats' or
                obj2._meta.app_label == 'vk_audio_stats'):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'vk_audio_stats':
            return db == 'audios_db'
        return None


class Genre(models.Model):
    name = models.CharField(max_length=20, unique=True)


class Subgenre(models.Model):
    name = models.CharField(max_length=20, unique=True)


class Artist(models.Model):
    name = models.CharField(max_length=64, unique=True)
    genre = models.ForeignKey(Genre, on_delete=models.DO_NOTHING)
    subgenre = models.ForeignKey(Subgenre, on_delete=models.DO_NOTHING)


class VkUser(models.Model):
    vk_id = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)


class User2Artist(models.Model):
    vk_user = models.ForeignKey(VkUser, on_delete=models.CASCADE)
    artist = models.ForeignKey(Artist, on_delete=models.DO_NOTHING)
    tracks = models.PositiveIntegerField()


