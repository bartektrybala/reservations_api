from .views import *
from django.urls import path

urlpatterns = [
    path('tables/', AvailableTablesView.as_view()),
    path('reservations/', ReservationsView.as_view()),
    path('reservations/<int:id>', CancelReservationView.as_view()),
]