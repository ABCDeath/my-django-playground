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

    def __str__(self):
        return self.name


class Subgenre(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Artist(models.Model):
    name = models.CharField(max_length=64, unique=True)
    genre = models.ForeignKey(Genre, on_delete=models.DO_NOTHING,
                              null=True, blank=True)
    subgenre = models.ForeignKey(Subgenre, on_delete=models.DO_NOTHING,
                                 null=True, blank=True)

    def __str__(self):
        return f'{self.name} ({self.subgenre or ""} {self.genre or ""})'


class VkUser(models.Model):
    vk_id = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    artists = models.ManyToManyField(Artist, through='ArtistCount')

    def __str__(self):
        return f'{self.vk_id}: {self.name}'


class ArtistCount(models.Model):
    vk_user = models.ForeignKey(VkUser, on_delete=models.DO_NOTHING)
    artist = models.ForeignKey(Artist, on_delete=models.DO_NOTHING)
    tracks_num = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.vk_user} - {self.artist} - {self.tracks_num}'
