from django.db import models


class NotesDBRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'notes_app':
            return 'notes_db'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'notes_app':
            return 'notes_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (obj1._meta.app_label == 'notes_app' or
                obj2._meta.app_label == 'notes_app'):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'notes_app':
            return db == 'notes_db'
        return None


class Note(models.Model):
    caption = models.CharField(max_length=64)
    type = models.CharField(max_length=32, default='note')
    text = models.CharField(max_length=1024)
    date = models.DateTimeField('date created')

    def __str__(self):
        return '({}) {}: {}'.format(self.date, self.caption, self.text)
