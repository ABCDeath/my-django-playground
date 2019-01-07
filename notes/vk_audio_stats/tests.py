from django.db import transaction
from django.db.models import Sum, Count
from django.test import TestCase

from .models import Artist, Genre, Subgenre, Track, VkUser


def prepare_data():
    """
    Функция создает данные в таблице:
        Пользователь Heisenberg:
            artist_1 - track_1 (subgenre_1 genre_1)
            artist_1 - track_2 (subgenre_2 genre_1)
            artist_2 - track_3 (subgenre_1 genre_1)
            artist_3 - track_1 (subgenre_1 genre_2)

        Пользователь Cat Whiskers:
            artist_1 - track_1 (subgenre_1 genre_1)
            artist_1 - track_3 (subgenre_1 genre_2)
            artist_2 - track_4 (subgenre_1 genre_3)
            artist_4 - track_5 (subgenre_3 genre_1)

        Пользователь Gordon Freeman:
            artist_1 - track_1 (subgenre_1 genre_1)
            artist_1 - track_3 (subgenre_1 genre_2)
            artist_2 - track_6 (subgenre_3 genre_1)
            artist_5 - track_7 (subgenre_2 genre_1)
    """

    with transaction.atomic():
        for genre in ['genre_1', 'genre_2', 'genre_3']:
            Genre(name=genre).save()

        for sub in ['subgenre_1', 'subgenre_2', 'subgenre_3']:
            Subgenre(name=sub).save()

        for artist in ['artist_1', 'artist_2', 'artist_3',
                       'artist_4', 'artist_5']:
            Artist(name=artist).save()

    users = {
        'user_1': 'Heisenberg',
        'user_2': 'Cat Whiskers',
        'user_3': 'Gordon Freeman'
    }

    tracks = {
        'user_1': [
            ('artist_1', 'track_1'),
            ('artist_1', 'track_2'),
            ('artist_2', 'track_3'),
            ('artist_3', 'track_1')
        ],
        'user_2': [
            ('artist_1', 'track_1'),
            ('artist_1', 'track_3'),
            ('artist_2', 'track_4'),
            ('artist_4', 'track_5')
        ],
        'user_3': [
            ('artist_1', 'track_1'),
            ('artist_1', 'track_3'),
            ('artist_2', 'track_6'),
            ('artist_5', 'track_7')
        ]
    }

    with transaction.atomic():
        for user in tracks:
            u = VkUser(vk_id=user, name=users[user])
            u.save()

            for artist, name in tracks[user]:
                t, created = Track.objects.get_or_create(
                    title=name, artist=Artist.objects.get(name=artist))
                if created:
                    t.save()
                u.tracks.add(t)

    tags = {
        ('artist_1', 'track_1'): ('genre_1', 'subgenre_1'),
        ('artist_1', 'track_2'): ('genre_1', 'subgenre_2'),
        ('artist_2', 'track_3'): ('genre_1', 'subgenre_1'),
        ('artist_3', 'track_1'): ('genre_2', 'subgenre_1'),
        ('artist_1', 'track_3'): ('genre_2', 'subgenre_1'),
        ('artist_2', 'track_4'): ('genre_3', 'subgenre_1'),
        ('artist_4', 'track_5'): ('genre_1', 'subgenre_3'),
        ('artist_2', 'track_6'): ('genre_1', 'subgenre_3'),
        ('artist_5', 'track_7'): ('genre_1', 'subgenre_2')
    }

    for artist, title in tags:
        a = Artist.objects.get(name=artist)
        g = Genre.objects.get(name=tags[(artist, title)][0])
        s = Subgenre.objects.get(name=tags[(artist, title)][1])

        t = Track.objects.get(artist=a, title=title)
        t.genre, t.subgenre = g, s
        t.save()


class TrackModelTest(TestCase):
    multi_db = True

    def prepare_data(self):
        with transaction.atomic():
            for genre in ['genre_1', 'genre_2', 'genre_3']:
                Genre(name=genre).save()

            for sub in ['subgenre_1', 'subgenre_2', 'subgenre_3']:
                Subgenre(name=sub).save()

            for artist in ['artist_1', 'artist_2', 'artist_3',
                           'artist_4', 'artist_5']:
                Artist(name=artist).save()

    def test_add(self):
        self.prepare_data()

        a = Artist.objects.get(name='artist_1')
        g = Genre.objects.get(name='genre_1')
        s = Subgenre.objects.get(name='subgenre_1')

        t = Track(title='title_1', artist=a, genre=g, subgenre=s)
        t.save()

        self.assertQuerysetEqual()


    def test_retrieve(self):
        self.prepare_data()

        users = {
            'user_1': 'Heisenberg',
            'user_2': 'Cat Whiskers',
            'user_3': 'Gordon Freeman'
        }

        tracks = {
            'user_1': [
                ('artist_1', 'track_1'),
                ('artist_1', 'track_2'),
                ('artist_2', 'track_3'),
                ('artist_3', 'track_1')
            ],
            'user_2': [
                ('artist_1', 'track_1'),
                ('artist_1', 'track_3'),
                ('artist_2', 'track_4'),
                ('artist_4', 'track_5')
            ],
            'user_3': [
                ('artist_1', 'track_1'),
                ('artist_1', 'track_3'),
                ('artist_2', 'track_6'),
                ('artist_5', 'track_7')
            ]
        }

        with transaction.atomic():
            for user in tracks:
                u = VkUser(vk_id=user, name=users[user])
                u.save()

                for artist, name in tracks[user]:
                    t, created = Track.objects.get_or_create(
                        title=name, artist=Artist.objects.get(name=artist))
                    if created:
                        t.save()
                    u.tracks.add(t)

        tags = {
            ('artist_1', 'track_1'): ('genre_1', 'subgenre_1'),
            ('artist_1', 'track_2'): ('genre_1', 'subgenre_2'),
            ('artist_2', 'track_3'): ('genre_1', 'subgenre_1'),
            ('artist_3', 'track_1'): ('genre_2', 'subgenre_1'),
            ('artist_1', 'track_3'): ('genre_2', 'subgenre_1'),
            ('artist_2', 'track_4'): ('genre_3', 'subgenre_1'),
            ('artist_4', 'track_5'): ('genre_1', 'subgenre_3'),
            ('artist_2', 'track_6'): ('genre_1', 'subgenre_3'),
            ('artist_5', 'track_7'): ('genre_1', 'subgenre_2')
        }

        for artist, title in tags:
            a = Artist.objects.get(name=artist)
            g = Genre.objects.get(name=tags[(artist, title)][0])
            s = Subgenre.objects.get(name=tags[(artist, title)][1])

            t = Track.objects.get(artist=a, title=title)
            t.genre, t.subgenre = g, s
            t.save()

        # общие жанры пользователя с остальными

        heisenberg_genres = {
            x[0]: x[1] for x in
            (VkUser.objects.get(name='Heisenberg').
                tracks.values_list('genre__name').annotate(Count('genre')))
        }

        others = VkUser.objects.all().exclude(name='Heisenberg')
        others_genres = {
            u.name: {
                x[0]: x[1] for x in
                u.tracks.filter(genre__name__in=heisenberg_genres).
                    values_list('genre__name').annotate(Count('genre'))
            } for u in others
        }

        common = {
            user_name: {
                name: min(genres[name], heisenberg_genres[name])
                for name in genres
            } for user_name, genres in others_genres.items()
        }

        self.assertDictEqual(common['Cat Whiskers'],
                             {'genre_1': 2, 'genre_2': 1})

        self.assertDictEqual(common['Gordon Freeman'],
                             {'genre_1': 3, 'genre_2': 1})
