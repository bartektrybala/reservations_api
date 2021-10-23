Reservations API in Django Rest Framework for restaurant.
Endpoint:
- GET /tables - return available tables at a certain time and with the right number of places
- GET /reservations - allows restaurant staff to download a list of all bookings on a given day.
- POST /reservations - allows the customer to make a new reservation for a table
- PUT /reservations/{id} - allows the customer to send a request to cancel the booking. The customer receives an email with a verification code
- DELETE /reservations/{id} - customer cofirm cancellation of reservation with received verification code
