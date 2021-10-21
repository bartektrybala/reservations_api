from django.core.mail import send_mail
from django.http import Http404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from datetime import datetime, time, timedelta
from rich import print

from tables.models import Table, Reservation
from tables.serializers import ReservationSerializer, TableSerializer
from reservations_api import settings


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
                            "tableNumber": "2",
                            "fullName": "Paul Smith",
                            "phone": "997 123 997",
                            "email": "paul@email.com",
                            "numberOfSeats": "5"
                        }" -X POST

            curl -L localhost:5000/reservations/ -H "Content-Type: application/json" -d '{"date": "2021-10-19 16:22:50.123", "duration": "3", "tableNumber": "14", "fullName": "Paul Smith", "phone": "997 123 997", "email": "paul@email.com", "numberOfSeats": "5"}' -X POST
        """
        date = get_date_from_request(request.data['date'])
        duration = int(request.data['duration'])
        full_name = request.data['fullName']
        phone = request.data['phone']
        email = request.data['email']
        number_of_seats = int(request.data['numberOfSeats'])
        table = Table.objects.get(number=request.data['tableNumber'])

        if table in AvailableTablesView.get_available_tables(number_of_seats, date, duration):
            return self.make_reservation(date, duration, table, full_name, phone, email, number_of_seats)
        else:
            return Response(status=status.HTTP_409_CONFLICT)

    def make_reservation(self, date, duration, table, full_name, phone, email, number_of_seats):
        try:
            r = Reservation(
                table = table,
                date = date,
                duration = duration,
                full_name = full_name,
                phone = phone,
                email = email,
                number_of_seats = number_of_seats
            )
            r.save()
            self.send_confirmation_email(table, date, duration, full_name, phone, number_of_seats, email)
            return Response(status=status.HTTP_201_CREATED)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def send_confirmation_email(self, table, date, duration, full_name, phone, number_of_seats, email):
        message = "Reservation details:\n Table: {table}\n Date: {date}\n Duration: {duration}\n"\
                    "Full name: {full_name}\n Phone: {phone}\n Number of seats: {number_of_seats}".format(
                        table=table, date=date, duration=duration, full_name=full_name, phone=phone, number_of_seats=number_of_seats)
        send_mail("Reservation confirmation", message, settings.EMAIL_HOST_USER, [email], fail_silently=False)



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
        duration = int(request.GET.get('duration'))
        status = request.GET.get('status')
        if status == "free":

            available_tables = AvailableTablesView.get_available_tables(min_seats, start_date, duration)
            serializer = TableSerializer(available_tables, many=True)
            return Response(serializer.data)
        else:
            return Response()
    
    @staticmethod
    def get_available_tables(min_seats, start_date, duration):
        """
            Auxliary function to check free tables.

            Return:
                Table objects
                    * satisfied min_seats condition
                    * excluded reserved tables
        """
        finish_date = start_date + timedelta(hours=duration)
        reservations = AvailableTablesView.get_ongoing_reservations(start_date, finish_date)
        seat_filter = Q(min_number_of_seats__lte=min_seats) & Q(max_number_of_seats__gte=min_seats)
        return Table.objects.filter(seat_filter).exclude(id__in=reservations.values_list('table'))

    @staticmethod
    def get_ongoing_reservations(start_date, finish_date):
        ongoing_reservations_ids = []

        for r in Reservation.objects.filter(date__date=start_date):
            if AvailableTablesView.duration_overlap(r, start_date, finish_date):
                ongoing_reservations_ids.append(r.id)
        return Reservation.objects.filter(id__in=ongoing_reservations_ids)
    
    @staticmethod
    def duration_overlap(reservation, start_date, finish_date):
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