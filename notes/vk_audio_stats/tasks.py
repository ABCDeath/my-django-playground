import json
import os
import sys

from functools import reduce
from operator import or_

# import django
# from celery import Celery
import redis
from celery.utils.log import get_task_logger
from django.db.models import Q

from . import background_searcher
from notes.celery import background_worker

# sys.path.extend([os.getenv('DJANGO_PROJECT_PATH')])
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notes.settings")
# django.setup()

from vk_audio_stats.models import Artist, Genre, Track, VkUser

# REDIS_SERVER = 'redis://localhost:6379/0'
# background_worker = Celery('tasks', backend=REDIS_SERVER, broker=REDIS_SERVER)

logger = get_task_logger(__name__)
redis_client = redis.Redis()


@background_worker.task
def dummy(vk_id):
    redis_set_user_update_status(vk_id)
    import time
    logger.info(f'dummy task {vk_id}')
    time.sleep(5)
    redis_set_user_update_status(vk_id, False)
    logger.info(f'dummy task {vk_id} finished')



def get_credentials():
    with open('vk_audio_stats/credentials.json') as cred_file:
        credentials = json.load(cred_file)
    return credentials

def redis_set_user_update_status(vk_id, state=True):
    redis_client.set(f'update state {vk_id}',
                     'in progress' if state else 'finished')

@background_worker.task
def db_update_user(vk_id):
    redis_set_user_update_status(vk_id)

    credentials = get_credentials()
    vk_api = background_searcher.VkApiLockable(credentials['vk'])

    username = vk_api.username(vk_id)

    user_object, created = (
        VkUser.objects.prefetch_related('friends')
            .get_or_create(vk_id=vk_id,
                           defaults={'vk_id': vk_id, 'name': username}))
    if created:
        user_object.save()

    logger.info(f'пользователь {username} ({vk_id}) '
                f'{"создан" if created else "уже существует"}')

    user_friends = vk_api.friends(vk_id)

    logger.info(f'задачи обновление друзей и треков {vk_id}')

    tasks = [db_update_user_friends.si(vk_id, user_friends),
             db_update_tracks.si(vk_id, vk_api.track_list(vk_id))]
    tasks.extend([db_update_tracks.si(uid, vk_api.track_list(uid))
                  for uid in user_friends])
    tasks.append(finish.si(vk_id))

    task_chain = reduce(or_, tasks)

    task_chain()


@background_worker.task
def db_update_user_friends(vk_id, friends):
    user_object = (VkUser.objects.prefetch_related('friends')
                   .get(vk_id=vk_id))

    friends = {int(uid): name for uid, name in friends.items()}

    users_in_db = (VkUser.objects
                   .filter(vk_id__in=[user_id for user_id in friends])
                   .values_list('vk_id', flat=True))

    users_to_add = {uid: name for uid, name in friends.items()
                    if uid not in users_in_db}

    objs = (VkUser(vk_id=vk_id, name=name)
            for vk_id, name in users_to_add.items())
    VkUser.objects.bulk_create(objs)

    logger.info(f'{vk_id} добавлено пользователей '
                f'{len(users_to_add)}: {users_to_add}')

    user_friends_in_db = [u.vk_id for u in user_object.friends.all()]
    friends_to_add = (VkUser.objects.filter(vk_id__in=friends)
                      .exclude(vk_id__in=user_friends_in_db))
    user_object.friends.add(*friends_to_add)

    logger.info(f'{vk_id} добавлено {len(friends_to_add)}: {friends_to_add}')

    friends_to_delete = [u for u in user_friends_in_db if u not in friends]
    objs = VkUser.objects.filter(vk_id__in=friends_to_delete)
    user_object.friends.remove(*objs)

    logger.info(
        f'{vk_id} удалено {len(friends_to_delete)}: {friends_to_delete}')


@background_worker.task
def db_update_tracks(vk_id, track_list):
    if not track_list:
        return

    user_object = VkUser.objects.prefetch_related('tracks').get(vk_id=vk_id)

    new_artists = set(a for a, t in track_list
                      if not Artist.objects.filter(name=a).exists() and
                      len(a) <= Artist._meta.get_field('name').max_length)

    objs = (Artist(name=a) for a in new_artists)
    Artist.objects.bulk_create(objs)

    logger.info(f'{vk_id}: добавлено {len(new_artists)} исполнителей в бд.')

    new_tracks = list(
        set((a, t) for a, t in track_list
            if a in new_artists and
            not Track.objects.filter(title=t, artist__name=a).exists() and
            len(t) <= Track._meta.get_field('title').max_length))

    objs = (Track(title=t, artist=Artist.objects.get(name=a))
            for a, t in new_tracks)
    Track.objects.bulk_create(objs)

    logger.info(f'{vk_id}: добавлено {len(new_tracks)} треков в бд.')

    db_update_track_genre.delay(new_tracks)

    condition = reduce(or_, [Q(title=t, artist__name=a) for a, t in track_list])
    tracks_to_add = (Track.objects.filter(condition)
                     .difference(user_object.tracks.all()))

    user_object.tracks.add(*tracks_to_add)

    logger.info(f'пользователю {vk_id} добавлено {tracks_to_add.count()}')

    tracks_to_remove = (user_object.tracks.all()
                        .difference(Track.objects.filter(condition)))
    user_object.tracks.remove(*tracks_to_remove)

    logger.info(f'у пользователя {vk_id} удалено {tracks_to_remove.count()}')


@background_worker.task
def db_update_track_genre(track_list):
    credentials = get_credentials()

    tag_finder = background_searcher.TagFinderLockable(credentials['discogs'])

    for artist, track in track_list:
        logger.info(f'поиск жанра {artist} - {track}')
        genre = tag_finder.find(artist, track)
        if not genre:
            continue

        logger.info(f'трек {artist} - {track} ({genre})')

        genre_object, created = Genre.objects.get_or_create(
            name=genre, defaults={'name': genre})
        if created:
            genre_object.save()

        # TODO: разобраться, откуда берутся одинаковые треки
        if (Track.objects.prefetch_related('vkuser_set')
                .filter(title=track, artist__name=artist).count() > 1):
            track_objects = sorted(
                Track.objects.prefetch_related('vkuser_set')
                    .filter(title=track, artist__name=artist),
                key=lambda x: x.vkuser_set.count(), reverse=True)
            actual = track_objects[0]
            to_delete = track_objects[1:]

            for t_obj in to_delete:
                users = t_obj.vkuser_set.all()
                actual.vkuser_set.add(*users)
                t_obj.vkuser_set.remove(*users)
                t_obj.delete()

        track_object = Track.objects.get(title=track, artist__name=artist)
        track_object.genre = genre_object
        track_object.save()

@background_worker.task
def finish(vk_id):
    redis_set_user_update_status(vk_id, False)
    logger.info(f'обновление {vk_id} завершено')
