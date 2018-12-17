from django.db import transaction
from django.test import TestCase

from .models import Artist, Genre, Subgenre, Tracks, VkUser


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

