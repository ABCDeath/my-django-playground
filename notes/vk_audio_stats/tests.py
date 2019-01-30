from django.db import transaction
from django.db.models import Count, Q
from django.test import TestCase

from .models import Artist, Genre, Track, VkUser


def prepare_data():
    """
    Функция создает данные в таблице:
        Пользователь Heisenberg:
            artist_1 - track_1 (hard rock)
            artist_1 - track_2 (post rock)
            artist_2 - track_3 (post metal)
            artist_3 - track_1 (hard bop)
            artist_4 - track_4 (post rock)

        Пользователь Cat Whiskers:
            artist_1 - track_4 (punk rock)
            artist_1 - track_3 (post rock)
            artist_2 - track_4 (blues)
            artist_1 - track_1 (hard rock)
            artist_2 - track_5 (post metal)

        Пользователь Gordon Freeman:
            artist_1 - track_1 (hard rock)
            artist_1 - track_3 (post rock)
            artist_2 - track_6 (blues)
            artist_5 - track_7 (rap)
            artist_2 - track_4 (blues)
    """

    with transaction.atomic():
        for genre in ['hard rock', 'post rock', 'post metal', 'hard bop',
                      'punk rock', 'blues', 'rap']:
            Genre(name=genre).save()

        for artist in ['artist_1', 'artist_2', 'artist_3',
                       'artist_4', 'artist_5']:
            Artist(name=artist).save()

    users = {
        1: 'Heisenberg',
        2: 'Cat Whiskers',
        3: 'Gordon Freeman'
    }

    tracks = {
        'user_1': [
            ('artist_1', 'track_1'),
            ('artist_1', 'track_2'),
            ('artist_2', 'track_3'),
            ('artist_3', 'track_1'),
            ('artist_4', 'track_4')
        ],
        'user_2': [
            ('artist_1', 'track_4'),
            ('artist_1', 'track_3'),
            ('artist_2', 'track_4'),
            ('artist_1', 'track_1'),
            ('artist_2', 'track_5')
        ],
        'user_3': [
            ('artist_1', 'track_1'),
            ('artist_1', 'track_3'),
            ('artist_2', 'track_6'),
            ('artist_5', 'track_7'),
            ('artist_2', 'track_4')
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
        ('artist_1', 'track_1'): 'hard rock',
        ('artist_1', 'track_2'): 'post rock',
        ('artist_2', 'track_3'): 'post metal',
        ('artist_3', 'track_1'): 'hard bop',
        ('artist_4', 'track_4'): 'post rock',

        ('artist_1', 'track_4'): 'punk rock',
        ('artist_1', 'track_3'): 'post rock',
        ('artist_2', 'track_4'): 'blues',
        ('artist_2', 'track_5'): 'post metal',

        ('artist_2', 'track_6'): 'blues',
        ('artist_5', 'track_7'): 'rap'
    }

    for artist, title in tags:
        a = Artist.objects.get(name=artist)

        t = Track.objects.get(artist=a, title=title)
        t.genre = Genre.objects.get(name=tags[(artist, title)])
        t.save()


class TrackModelTest(TestCase):
    multi_db = True

    def test_retrieve_users_by_genre(self):
        prepare_data()

        q = (Track.objects.filter(genre__name__contains='rock')
             .values_list('vkuser__name').annotate(Count('vkuser__name')))

        users_tracks = {name: count for name, count in q}

        self.assertDictEqual(
            users_tracks,
            {'Heisenberg': 3, 'Cat Whiskers': 3, 'Gordon Freeman': 2})

    def test_retrieve_users_by_diff_genres(self):
        prepare_data()

        condition = (Q(genre__name__contains='post') &
                     (Q(genre__name__contains='rock') |
                      Q(genre__name__contains='metal')))

        q = (Track.objects.filter(condition).values_list('vkuser__name')
             .annotate(Count('vkuser__name')))

        users_tracks = {name: count for name, count in q}

        self.assertDictEqual(
            users_tracks,
            {'Heisenberg': 3, 'Cat Whiskers': 2, 'Gordon Freeman': 1})

    def test_retrieve_common_subgenres_for_all_users(self):
        prepare_data()

        userlist = VkUser.objects.all()
        tracks = (Track.objects.filter(vkuser__in=userlist)
                  .values_list('genre__name', 'vkuser__name')
                  .annotate(Count('genre')))
        group_by_genre = {x[0]: [] for x in tracks}
        [group_by_genre[x[0]].append((x[1], x[2])) for x in tracks]

        result = {g: sorted(u, key=lambda x: x[0])
                  for g, u in group_by_genre.items()
                  if len(u) == len(userlist)}

        self.assertDictEqual(
            result,
            {
                'hard rock': sorted(
                    [('Heisenberg', 1), ('Cat Whiskers', 1),
                     ('Gordon Freeman', 1)], key=lambda x: x[0]),
                'post rock': sorted(
                    [('Heisenberg', 2), ('Cat Whiskers', 1),
                     ('Gordon Freeman', 1)], key=lambda x: x[0])
            }
        )


class VkUserModelTest(TestCase):
    multi_db = True

    def test_retrieve_user_common_genres(self):
        prepare_data()

        heisenberg_genres = {
            x[0]: x[1] for x in
            (VkUser.objects.get(name='Heisenberg').
             tracks.values_list('genre__name').annotate(Count('genre')))
        }

        others = VkUser.objects.all().exclude(name='Heisenberg')
        others_genres = {
            u.name: {
                x[0]: x[1] for x in
                u.tracks.filter(genre__name__in=heisenberg_genres)
                        .values_list('genre__name').annotate(Count('genre'))
            } for u in others
        }

        common = {
            user_name: {
                name: min(genres[name], heisenberg_genres[name])
                for name in genres
            } for user_name, genres in others_genres.items()
        }

        self.assertDictEqual(common['Cat Whiskers'],
                             {'hard rock': 1, 'post rock': 1, 'post metal': 1})

        self.assertDictEqual(common['Gordon Freeman'],
                             {'hard rock': 1, 'post rock': 1})
