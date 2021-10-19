# Generated by Django 3.2.8 on 2021-10-18 15:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tables', '0002_table_number'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('duration', models.IntegerField()),
                ('seat_number', models.IntegerField()),
                ('full_name', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=31)),
                ('email', models.EmailField(max_length=254)),
                ('number_of_seats', models.IntegerField()),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tables.table')),
            ],
        ),
    ]
