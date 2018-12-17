from django.db import transaction
from django.test import TestCase

from .models import Artist, Genre, Subgenre, ArtistCount, VkUser


class ArtistModelTest(TestCase):
    multi_db = True

    def test_add(self):
        with transaction.atomic():
            for genre in ['rock', 'bop']:
                Genre(name=genre).save()

            for sub in ['post', 'hard', 'punk']:
                Subgenre(name=sub).save()

        artists = [
            ('art_punk-0', 'punk', 'rock'),
            ('art_punk-1', 'punk', 'rock'),
            ('art_bop', 'hard', 'bop'),
            ('art_no_sub', '', 'bop'),
            ('art_no_genre', '', ''),
            ('art_post_rock', 'post', 'rock'),
            ('art_post_bop', 'post', 'bop')
        ]

        with transaction.atomic():
            for name, sub, genre in artists:
                g = Genre.objects.filter(name=genre) or [None]
                s = Subgenre.objects.filter(name=sub) or [None]
                Artist(name=name, genre=g[0], subgenre=s[0]).save()

        self.assertQuerysetEqual(
            Artist.objects.all().order_by('pk'),
            [f'<Artist: {name} ({sub} {genre})>'
             for name, sub, genre in artists]
        )

        self.assertQuerysetEqual(
            Artist.objects.filter(genre__name__exact='rock').order_by('pk'),
            [f'<Artist: {name} ({sub} {genre})>'
             for name, sub, genre in artists if genre == 'rock']
        )

        self.assertQuerysetEqual(
            Artist.objects.filter(
                genre__name__exact='rock',
                subgenre__name__exact='punk').order_by('pk'),
            [f'<Artist: {name} ({sub} {genre})>'
             for name, sub, genre in artists
             if genre == 'rock' and sub == 'punk']
        )

    def test_update_after_add(self):
        Genre(name='genre').save()
        Subgenre(name='subgenre').save()
        Artist(name='artist').save()
        a = Artist.objects.get(name='artist')
        a.genre = Genre.objects.get(name='genre')
        a.subgenre = Subgenre.objects.get(name='subgenre')
        a.save()

        self.assertQuerysetEqual(
            Artist.objects.all(), ['<Artist: artist (subgenre genre)>'])


class ArtistCountModelTest(TestCase):
    def prepair_data(self):
        with transaction.atomic():
            Genre(name='rock').save()

            for sub in ['post', 'hard', 'punk']:
                Subgenre(name=sub).save()

            VkUser(vk_id='1', name='a b').save()
            VkUser(vk_id='2', name='c d').save()

        artists = [
            ('art_punk-0', 'punk', 'rock'),
            ('art_punk-1', 'punk', 'rock'),
            ('art_no_genre', '', ''),
            ('art_post_rock', 'post', 'rock'),
        ]

        with transaction.atomic():
            for name, sub, genre in artists:
                g = Genre.objects.filter(name=genre) or [None]
                s = Subgenre.objects.filter(name=sub) or [None]
                Artist(name=name, genre=g[0], subgenre=s[0]).save()

        tracks = [
            ('1', 'art_punk-0', 3),
            ('1', 'art_punk-1', 4),
            ('1', 'art_no_genre', 2),
            ('2', 'art_punk-0', 2),
            ('2', 'art_no_genre', 5),
            ('2', 'art_post_rock', 9)
        ]

        with transaction.atomic():
            for vk_id, artist_name, tracks_number in tracks:
                artist = Artist.objects.get(name=artist_name)
                vk_user = VkUser.objects.get(vk_id=vk_id)
                ArtistCount(vk_user=vk_user, artist=artist,
                            tracks_num=tracks_number).save()

        return tracks

    def test_add(self):
        self.prepair_data()

        # TODO: попробовать выбрать общие
        self.assertQuerysetEqual(
            ArtistCount.objects.filter(
                artist__genre__name='rock', artist__subgenre__name='punk'
            ).order_by('pk'), [''])

    def test_delete(self):
        tracks = self.prepair_data()

        deleted = ArtistCount.objects.filter(
            vk_user__vk_id='1', artist__name='art_punk-0').delete()

        self.assertEqual(deleted[1]['vk_audio_stats.ArtistCount'], 1)

        self.assertFalse(
            ArtistCount.objects.filter(
                vk_user__vk_id='1', artist__name='art_punk-0'))

        self.assertListEqual(
            [(x.vk_user.vk_id, x.artist.name, x.tracks_num)
             for x in ArtistCount.objects.all().order_by('pk')],
            tracks[1:]
        )

    def test_update(self):
        tracks = self.prepair_data()

        ac = ArtistCount.objects.get(
            vk_user__vk_id='1', artist__name='art_punk-0')
        ac.tracks_num = 7
        ac.save()

        tracks[0] = ('1', 'art_punk-0', 7)

        self.assertListEqual(
            [(x.vk_user.vk_id, x.artist.name, x.tracks_num)
             for x in ArtistCount.objects.all().order_by('pk')],
            tracks
        )
