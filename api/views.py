from typing import Type
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.http import Http404
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from datetime import datetime, time, timedelta, tzinfo
import random
from rich import print

from tables.models import Table, Reservation
from tables.serializers import ReservationSerializer, TableSerializer
from reservations_api import settings


class ReservationsView(APIView):
    def get(self, request):
        """
            Return list of reservations for the day.
            Example:
                curl -L 'localhost:5000/reservations?start_date=2021-10-18+00:00:00.000'
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

            curl -L localhost:5000/reservations/ -H "Content-Type: application/json" -d '{"date": "2021-10-19 16:22:50.123", "duration": "3", "tableNumber": "53", "fullName": "Paul Smith", "phone": "997 123 997", "email": "paul@email.com", "numberOfSeats": "2"}' -X POST
        """
        date = get_date_from_request(request.data['date'])
        duration = int(request.data['duration'])
        full_name = request.data['fullName']
        phone = request.data['phone']
        email = request.data['email']
        number_of_seats = int(request.data['numberOfSeats'])
        try:
            table = Table.objects.get(number=request.data['tableNumber'])
        except (Reservation.DoesNotExist, ValueError):
            return Response(status=status.HTTP_404_NOT_FOUND)

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
            r.full_clean()
        except ValidationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            r.save()
            self.send_confirmation_email(table, date, duration, full_name, phone, number_of_seats, email, r)
            return Response(status=status.HTTP_201_CREATED)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def send_confirmation_email(self, table, date, duration, full_name, phone, number_of_seats, email, reservation):
        message = "Reservation details:\n Table: {table}\n Date: {date}\n Duration: {duration}\n"\
                    "Full name: {full_name}\n Phone: {phone}\n Number of seats: {number_of_seats}\n"\
                    "Unique reservation number: {reservation_id}".format(
                        table=table, date=date.strftime("%Y-%m-%d %H:%M"), duration=duration, full_name=full_name, phone=phone, number_of_seats=number_of_seats,
                        reservation_id=reservation.id)
        send_mail(subject="Reservation confirmation", message=message, from_email=settings.EMAIL_HOST_USER, recipient_list=[email], fail_silently=False)


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
        try:
            min_seats = int(request.GET.get('min_seats'))
            duration = int(request.GET.get('duration'))
        except (ValueError, TypeError):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        start_date = get_date_from_request(request.GET.get('start_date'))
        request_status = request.GET.get('status')
        if request_status == "free":
            available_tables = AvailableTablesView.get_available_tables(min_seats, start_date, duration)
            serializer = TableSerializer(available_tables, many=True)
            return Response(serializer.data)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)
    
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


class CancelReservationView(APIView):
    def put(self, request, *args, **kwargs):
        """
            Create task for cancel reservation.
            Send generated verification code in email for cancel reservation.

            Example:
                curl -L 'localhost:5000/reservations/15' -H "Content-Type: application/json" -d '{"status": "requested cancellation"}' -X PUT
        """
        reservation_status = request.data['status']
        if reservation_status == 'requested cancellation':
            try:
                reservation = Reservation.objects.get(id=kwargs['id'])
            except (Reservation.DoesNotExist, ValueError):
                return Response(status=status.HTTP_404_NOT_FOUND)

            # check if requested cancellation is no later than 2 hours before
            if reservation.date.replace(tzinfo=None) - datetime.now() < timedelta(hours=2):
                return Response(status.HTTP_405_METHOD_NOT_ALLOWED)

            reservation.verification_code = random.randint(100000, 999999)
            reservation.save()

            send_mail("Confirmation of the cancellation of the reservation",
            "Code: {verification_code}".format(verification_code=reservation.verification_code),
            from_email=settings.EMAIL_HOST_USER, recipient_list=[reservation.email], fail_silently=False)

            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)
            

    def delete(self, request, *args, **kwargs):
        """
            Confirm cancelattion of reservation with verification code.
            Send email with confirmation about reservation cancelled.

            Example:
                curl -l localhost:5000/reservations/15 -H "Content-Type: application/json" -d '{"verification_code": "123456"}' -X DELETE
        """
        try:
            reservation = Reservation.objects.get(id=kwargs['id'])
        except (Reservation.DoesNotExist, ValueError):
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            v_code = int(request.data['verification_code']) 
        except (TypeError, ValueError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if  v_code == reservation.verification_code:
            reservation.delete()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_401_UNAUTHORIZED)


def get_date_from_request(date):
    try:
        return datetime.strptime(date, "%Y-%m-%d %H:%M:%S.%f")
    except (TypeError, ValueError):
        raise Http404
