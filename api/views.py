from django.shortcuts import render
from tables.models import Table, Reservation
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from rest_framework import serializers, status
from datetime import datetime, timedelta
from rich import print
from django.db.models import Q

from tables.serializers import ReservationSerializer, TableSerializer


class ReservationsView(APIView):
    """
        List reservations for the day, or create new reservation.
    """
    def get(self, request):
        """
            Example:
                curl -L 'localhost:5000/reservations?date=2021-10-18'
        """
        date_from_request = request.GET.get('date')
        try:
            # for invalid date type
            date = datetime.strptime(date_from_request, "%Y-%m-%d")
        except (TypeError, ValueError):
            raise Http404

        reservations = Reservation.objects.filter(date__date=date)
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        """

class AvailableTablesView(APIView):
    """
        List available tables at a certain time.
    """
    def get(self, request):
        """
            - 3 persons, 
            - booking at 16 on October 19
            - reservation for 3 hours

            Example:
                curl -l 'localhost:5000/tables?status=200&min_seats=3&start_date=2021-10-19-16&duration=3
            
            Return:
                Array: []
        """
        min_seats = request.GET.get('min_seats')
        start_date_from_request = request.GET.get('start_date')
        duration = request.GET.get('duration')
        try:
            start_date = datetime.strptime(start_date_from_request, "%Y-%m-%d-%H")
        except (TypeError, ValueError):
            raise Http404
            

        available_tables = self.get_available_tables(min_seats, start_date, int(duration))
        serializer = TableSerializer(available_tables, many=True)
        return Response(serializer.data)
    
    def get_available_tables(self, min_seats, start_date, duration):
        """
            Auxliary function to check free tables.

            Return:
                Table objects
                    * satisfied min_seats condition
                    * excluded reserved tables
        """
        hours_range = [start_date.hour, (start_date + timedelta(hours=duration)).hour+1]
        reservations = self.get_ongoing_reservations(start_date, hours_range)
        return Table.objects.filter(min_number_of_seats__lte=min_seats, max_number_of_seats__gte=min_seats)\
            .exclude(id__in=reservations.values_list('table'))


    def get_ongoing_reservations(self, start_date, hours_range):
        extracted_hours_range = range(hours_range[0], hours_range[1])
        ongoing_reservations_ids = []

        for r in Reservation.objects.filter(date__date=start_date):
            if self.duration_overlap(r, extracted_hours_range):
                ongoing_reservations_ids.append(r.id)
        return Reservation.objects.filter(id__in=ongoing_reservations_ids)
    
    def duration_overlap(self, reservation, extracted_hours_range):
        # check every possibility
        if reservation.date.hour in extracted_hours_range:
            return True
        elif reservation.finish_hour() in extracted_hours_range:
            return True
        elif reservation.date.hour < extracted_hours_range[0] and reservation.finish_hour() > extracted_hours_range[-1]:
            return True
        else:
            return False