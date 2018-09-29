from django.db import models

class Note(models.Model):
    caption = models.CharField(max_length=64)
    type = models.CharField(max_length=32, default='note')
    text = models.CharField(max_length=1024)
    date = models.DateTimeField('date created')

    def __str__(self):
        return '({}) {}: {}'.format(self.date, self.caption, self.text)
