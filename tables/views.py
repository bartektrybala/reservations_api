from .models import Reservation
from django.http import JsonResponse


def available_tables(request, status, min_seats, start_date, duration):
    if request.method == 'GET':
        pass

def reservations(request, id=None):
    if request.method == 'GET':
        from rich import print
        date = request.GET.get('date', None)
        data = Reservation.objects.filter(date=date).values()
        return JsonResponse(list(data), safe=False)

def cancel_reservation(request, id):
    pass
