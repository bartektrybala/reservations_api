# Generated by Django 3.2.8 on 2021-10-21 20:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0006_remove_reservation_seat_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='verification_code',
            field=models.IntegerField(default=0),
        ),
    ]
