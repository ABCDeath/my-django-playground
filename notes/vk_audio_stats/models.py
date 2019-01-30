"""
┌──VkUser───┐        ┌──Track──────┐       ┌──Artist───┐
│* id       │  ┌────►│* id         │  ┌───►│* id       │
│  vk_id    │  │     │  title      │  │    │  name     │
│  name     │  │     │  artist     │──┘    └───────────┘
│  tracks   │──┘     │  genre      │────┐
└───────────┘        │  subgenre   │    │  ┌──Genre────┐
                     └─────────────┘    └─►│* id       │
                                           │  name     │
                                           └───────────┘
"""


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
    name = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return str(self.name).title()


class Artist(models.Model):
    name = models.CharField(max_length=64, unique=True)

    def __str__(self):
        return str(self.name).title()


class Track(models.Model):
    title = models.CharField(max_length=64, unique=False)
    artist = models.ForeignKey(Artist, on_delete=models.DO_NOTHING)
    genre = models.ForeignKey(Genre, on_delete=models.DO_NOTHING,
                              null=True, blank=True)

    def __str__(self):
        return f'"{str(self.title).title()}" by {str(self.artist).title()} ' \
               f'({self.genre or "".title()})'


class VkUser(models.Model):
    vk_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=64)
    tracks = models.ManyToManyField(Track)
    friends = models.ManyToManyField('self')

    def __str__(self):
        return f'{self.vk_id}: {self.name}'
