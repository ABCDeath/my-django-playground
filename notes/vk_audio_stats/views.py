import math

from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

import pandas as pd

from bokeh.embed import components
from bokeh.io import output_file, show
from bokeh.palettes import Category20
from bokeh.plotting import figure
from bokeh.transform import cumsum

from .models import Artist, Genre, Track, VkUser


def index(request):
    genre_list = [t.genre for t in
                  Track.objects.filter(vkuser__isnull=False).distinct('genre')]

    genre_user_count = {g[0]: g[1] for g in
                        Track.objects.filter(vkuser__isnull=False)
                            .values_list('genre__name')
                            .annotate(Count('vkuser__name'))}

    data = pd.Series(genre_user_count).reset_index(name='value').rename(
        columns={'index': 'genre'})
    data['angle'] = data['value'] / data['value'].sum() * 2 * math.pi
    data['color'] = Category20[len(genre_user_count)]

    p = figure(plot_height=350, title="Users for genre", toolbar_location=None,
               tools="hover", tooltips="@genre: @value", x_range=(-0.5, 1.0))
    p.wedge(x=0, y=1, radius=0.4,
            start_angle=cumsum('angle', include_zero=True),
            end_angle=cumsum('angle'),
            line_color="white", fill_color='color', legend='genre', source=data)

    p.axis.axis_label = None
    p.axis.visible = False
    p.grid.grid_line_color = None

    script, div = components(p)

    return render(request, 'vk_audio_stats/index.html',
                  {'genre_list': genre_list,
                   'script': script,
                   'div': div})
