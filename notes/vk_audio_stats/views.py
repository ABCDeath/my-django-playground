import functools
import math
import operator

from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

import pandas as pd

from bokeh.core.properties import value
from bokeh.embed import components
from bokeh.io import output_file, show
from bokeh.models import ColumnDataSource
from bokeh.palettes import Category20, Category20c, Spectral6
from bokeh.plotting import figure
from bokeh.transform import cumsum, dodge, factor_cmap

from .models import Artist, Genre, Track, VkUser


def genre_chart(title, genre_count):
    data = pd.Series(genre_count).reset_index(name='value').rename(
        columns={'index': 'genre'})
    data['angle'] = data['value'] / data['value'].sum() * 2 * math.pi
    data['color'] = (Category20c[len(genre_count)] if len(genre_count) > 2
                     else Category20c[3][:2])

    p = figure(plot_height=300, plot_width=400, title=title,
               toolbar_location=None,
               tools='hover', tooltips='@genre: @value', x_range=(-0.5, 1.0))
    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True),
            end_angle=cumsum('angle'),
            line_color='white', fill_color='color', legend='genre', source=data)

    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None

    script, div = components(p)

    return {'script': script, 'div': div}

def friends_common_genre_chart(title, common_genre_list):
    users = [u[0] for u in common_genre_list[list(common_genre_list.keys())[0]]]

    data = {g: [u[1] for u in items] for g, items in common_genre_list.items()}
    data['users'] = users

    source = ColumnDataSource(data=data)

    p = figure(x_range=users, plot_height=300, plot_width=400,
               title=title, toolbar_location=None)

    genres_num = len(common_genre_list)
    position_list = [x*0.1 for x in range(-(genres_num//2), genres_num//2 + 1)]
    if not genres_num % 2:
        position_list.remove(0)

    palette = Category20[genres_num if genres_num > 2 else 3]

    for i, (pos, genre) in enumerate(zip(position_list, common_genre_list)):
        p.vbar(x=dodge('users', pos, range=p.x_range), top=genre,
               width=0.2, source=source, color=palette[i], legend=value(genre))

    p.x_range.range_padding = 0.1
    p.xgrid.grid_line_color = None
    p.legend.location = 'top_left'
    p.legend.orientation = 'horizontal'

    script, div = components(p)

    return {'script': script, 'div': div}

def compatibility_chart(title, compatibility):
    users = list(compatibility.keys())
    source = ColumnDataSource(
        data=dict(users=users, compatibility=list(compatibility.values())))

    p = figure(x_range=users, y_range=(0, 100), plot_height=300,
               toolbar_location=None, title=title, tools='hover',
               tooltips=[('совместимость', '@compatibility')])
    p.vbar(x='users', top='compatibility', width=0.9, source=source,
           legend='users', line_color='white',
           fill_color=factor_cmap('users', palette=Spectral6, factors=users))

    p.xgrid.grid_line_color = None
    p.legend.orientation = 'horizontal'
    p.legend.location = 'top_center'

    script, div = components(p)

    return {'script': script, 'div': div}


def genre(request):
    genre_list = [t.genre for t in
                  Track.objects.filter(vkuser__isnull=False).distinct('genre')]

    genre_user_count = {g[0]: g[1] for g in
                        Track.objects.filter(vkuser__isnull=False)
                            .values_list('genre__name')
                            .annotate(Count('vkuser__name'))}

    chart = genre_chart('Users for genre', genre_user_count)

    # пользователи по выбранным жанрам
    genre_id_list = request.GET.getlist('genre')

    user_list = {}
    if genre_id_list:
        condition = functools.reduce(
            operator.or_,
            [Q(genre__id=int(genre_id)) for genre_id in genre_id_list])

        q = (Track.objects.filter(condition)
             .values_list('vkuser__name', 'genre__name')
             .annotate(Count('vkuser__name')))

        for name, genre, count in q:
            if name not in user_list:
                user_list[name] = {}

            user_list[name][genre.title()] = count

    return render(request, 'vk_audio_stats/genre_list.html',
                  {'genre_list': genre_list,
                   'checked_genre_list': [int(g) for g in genre_id_list],
                   'chart': chart,
                   'user_list': user_list})


class UserView(generic.DetailView):
    model = VkUser
    template_name = 'vk_audio_stats/user_detail.html'

    # context_object_name = 'user_details'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = context['object']
        user_friends = user.friends.all()

        user_genres = {
            x[0]: x[1] for x in
            (user.tracks.values_list('genre__name')
             .annotate(Count('genre')))
        }

        context['user_genre_chart'] = genre_chart(
            f'Жанры пользователя {user.name}', user_genres)

        condition = Q(vkuser__in=user_friends) | Q(vkuser=user)
        tracks = (Track.objects.filter(condition)
                  .values_list('genre__name', 'vkuser__name')
                  .annotate(Count('genre')))
        group_by_genre = {x[0]: [] for x in tracks}
        [group_by_genre[x[0]].append((x[1], x[2])) for x in tracks]

        common_for_all = {g: sorted(u, key=lambda x: x[0])
                          for g, u in group_by_genre.items()
                          if len(u) == len(user_friends)+1}

        context['all_friends_common_genre'] = friends_common_genre_chart(
            'Общие со всеми друзьями жанры', common_for_all)

        friends_genres = {
            u.name: {
                x[0]: x[1] for x in
                u.tracks.filter(genre__name__in=user_genres)
                .values_list('genre__name').annotate(Count('genre'))
            } for u in user_friends
        }

        common = {
            user_name: {
                name: min(genres[name], user_genres[name])
                for name in genres
            } for user_name, genres in friends_genres.items()
        }

        context['friend_common_genre_list'] = {
            name: genre_chart(f'Общие жанры с пользователем {name}', genre_list)
            for name, genre_list in common.items()
        }

        compatibility = {
            name: (100*sum(genres.values()) /
                   max(user.tracks.count(),
                       user.friends.get(name=name).tracks.count()))
            for name, genres in common.items()
        }

        context['friends_compatibility'] = compatibility_chart(
            'Музыкальная совместимость с друзьями', compatibility)

        return context
