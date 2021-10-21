from django.db import models
from django.db.models.deletion import CASCADE
from django.db.models.fields import CharField, DateTimeField, EmailField, IntegerField
from django.db.models.fields.related import ForeignKey
from datetime import timedelta

class Table(models.Model):
    number = models.IntegerField()
    min_number_of_seats = IntegerField()
    max_number_of_seats = IntegerField()

    def __str__(self):
        return str(self.number)

class Reservation(models.Model):
    table = ForeignKey("Table", on_delete=CASCADE)
    date = DateTimeField()
    duration = IntegerField()
    full_name = CharField(max_length=255)
    phone = CharField(max_length=31)
    email = EmailField()
    number_of_seats = IntegerField()

    def finish_hour(self):
        duration_time = timedelta(hours=int(self.duration))
        return self.date + duration_time 
