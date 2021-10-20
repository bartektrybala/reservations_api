import requests
import io

from django.shortcuts import render
from tables.models import Table, Reservation
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from rest_framework import serializers, status
from datetime import datetime, time, timedelta, tzinfo
from rich import print
from django.db.models import Q
from rest_framework.parsers import JSONParser

from tables.serializers import ReservationSerializer, TableSerializer


class ReservationsView(APIView):
    def get(self, request):
        """
            Return list of reservations for the day.
            Example:
                curl -L 'localhost:5000/reservations?start_date=2021-10-18'
        """
        date = get_date_from_request(request.GET.get('start_date'))

        reservations = Reservation.objects.filter(date__date=date)
        serializer = ReservationSerializer(reservations, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
            Create new reservation for a table.
            Example:
                curl -L 'localhost:5000/reservations/' -H "Content-Type: application/json" 
                        -d "{
                            "date": "2021-10-19+16:22:50.123",
                            "duration": "3",
                            "seatNumber": "2",
                            "fullName": "Paul Smith",
                            "phone": "997 123 997",
                            "email": "paul@email.com",
                            "numberOfSeats": "5"
                        }" -X POST

            curl -L localhost:5000/reservations/ -H "Content-Type: application/json" -d '{"date": "2021-10-19 16:22:50.123", "duration": "3", "seatNumber": "2", "fullName": "Paul Smith", "phone": "997 123 997", "email": "paul@email.com", "numberOfSeats": "5"}' -X POST
        """
        date = get_date_from_request(request.data['date'])
        duration = request.data['duration']
        seat_number = request.data['seatNumber']
        full_name = request.data['fullName']
        phone = request.data['phone']
        email = request.data['email']
        number_of_seats = request.data['numberOfSeats']

        url = self.build_get_free_tables_url(request.get_host(), number_of_seats, date, duration, "free")
        available_tables = requests.get(url)
        stream = io.BytesIO(available_tables.content)
        data = JSONParser().parse(stream)
        return Response()

    def build_get_free_tables_url(self, domain, min_seats, start_date, duration, status):
        url = "http://{domain}/tables?min_seats={min_seats}&start_date={start_date}&duration={duration}&status={status}"\
            .format(domain=domain, min_seats=min_seats, start_date=start_date, duration=duration, status=status)
        return url


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
                curl -L "localhost:5000/tables?min_seats=6&start_date=2021-10-19+16:22:50.123&duration=3&status=free"
            
            Return:
                Array: []
        """
        min_seats = request.GET.get('min_seats')
        start_date = get_date_from_request(request.GET.get('start_date'))
        duration = request.GET.get('duration')
        status = request.GET.get('status')
        if status == "free":

            available_tables = self.get_available_tables(min_seats, start_date, int(duration))
            serializer = TableSerializer(available_tables, many=True)
            return Response(serializer.data)
        else:
            return Response()
    
    def get_available_tables(self, min_seats, start_date, duration):
        """
            Auxliary function to check free tables.

            Return:
                Table objects
                    * satisfied min_seats condition
                    * excluded reserved tables
        """
        finish_date = start_date + timedelta(hours=duration)
        reservations = self.get_ongoing_reservations(start_date, finish_date)
        seat_filter = Q(min_number_of_seats__lte=min_seats) & Q(max_number_of_seats__gte=min_seats)
        return Table.objects.filter(seat_filter).exclude(id__in=reservations.values_list('table'))


    def get_ongoing_reservations(self, start_date, finish_date):
        ongoing_reservations_ids = []

        for r in Reservation.objects.filter(date__date=start_date):
            if self.duration_overlap(r, start_date, finish_date):
                ongoing_reservations_ids.append(r.id)
        return Reservation.objects.filter(id__in=ongoing_reservations_ids)
    
    def duration_overlap(self, reservation, start_date, finish_date):
        # naive aware confilct
        reservation.date = reservation.date.replace(tzinfo=None)
        # check every possibility
        if start_date <= reservation.date <= finish_date:
            return True
        elif start_date <= reservation.finish_hour() <= finish_date:
            return True
        elif reservation.date < start_date and reservation.finish_hour() > finish_date:
            return True
        else:
            return False

def get_date_from_request(date):
    try:
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    except (TypeError, ValueError):
                raise Http404