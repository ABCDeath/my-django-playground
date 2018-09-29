from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import Note


def notes_list(request):
    return render(request, 'notes_app/notes.html', {'notes': Note.objects.all()})

def note_details(request, note_id):
    note = get_object_or_404(Note, pk=note_id)

    return render(request, 'notes_app/details.html', {'note': note})

def note_editor(request, note_id):
    note = get_object_or_404(Note, pk=note_id) if note_id > 0 else None

    return render(request, 'notes_app/edit.html', {'note': note})
