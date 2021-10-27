from rest_framework import serializers
from .models import Reservation, Table
from django.db import models


class ReservationSerializer(serializers.Serializer):
    table = serializers.CharField(source='table.number')
    date = serializers.DateTimeField()
    duration = serializers.IntegerField()
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=31)
    email = serializers.EmailField()
    number_of_seats = serializers.IntegerField()

    def create(self, validated_data):
        return Reservation.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        instance.table = validated_data.get('table', instance.table)
        instance.date = validated_data.get('date', instance.date)
        instance.duration = validated_data.get('duration', instance.duration)
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.email = validated_data.get('email', instance.email)
        instance.number_of_seats = validated_data.get('number_of_seats', instance.number_of_seats)
        instance.save()
        return instance

class TableSerializer(serializers.Serializer):
    number = serializers.IntegerField()
    min_number_of_seats = serializers.IntegerField()
    max_number_of_seats = serializers.IntegerField()

    