from .views import *
from django.urls import path

urlpatterns = [
    # path('tables', available_tables, name='avalable_tables'),
    path('reservations/', ReservationsView.as_view()),
    path('tables/', AvailableTablesView.as_view()),
]