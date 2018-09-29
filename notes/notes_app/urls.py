from django.urls import path
from . import views

urlpatterns = [
    path(r'', views.notes_list, name='notes_list'),
    path(r'<int:note_id>/', views.note_details, name='note_details'),
    path(r'<int:note_id>/edit', views.note_editor, name='note_editor'),
    # url(r'^notes/*', views.notes)
]
