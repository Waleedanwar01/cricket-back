from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import secrets, requests, json
from .models import Book
from .serializers import BookSerializer
from datetime import timedelta, datetime
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from .authentication import CsrfExemptSessionAuthentication, CustomJWTAuthentication
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404

PRICE_PER_HOUR = 1500
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_brevo_email(to_email, subject, html_content, text_content=None):
    """Send email via Brevo API"""
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }
    payload = {
        "sender": {"name": "Cricket Court", "email": settings.DEFAULT_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content or subject,
    }
    response = requests.post(BREVO_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def check_booking_availability(date, start_time, hours):
    start_hour = start_time.hour
    requested_slots = []

    for h in range(hours):
        slot_hour = (start_hour + h) % 24
        requested_slots.append(f"{slot_hour:02d}:00")

    existing_bookings = Book.objects.filter(date=date).exclude(status="cancelled")
    conflicting_slots = []

    for booking in existing_bookings:
        booking_start = booking.time.hour
        booking_end = (booking_start + booking.hours) % 24

        for slot in requested_slots:
            slot_hour = int(slot.split(':')[0])
            if booking_start < booking_end:
                if booking_start <= slot_hour < booking_end:
                    conflicting_slots.append(slot)
            else:
                if slot_hour >= booking_start or slot_hour < booking_end:
                    conflicting_slots.append(slot)

    return conflicting_slots


@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def bookCourt(request):
    serializer = BookSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    booking = serializer.save(user=request.user)
    booking.confirmation_token = secrets.token_urlsafe(32)
    booking.save(update_fields=["confirmation_token", "updated_at"])

    start_dt = datetime.combine(booking.date, booking.time)
    end_dt = start_dt + timedelta(hours=int(booking.hours))
    total_price = int(booking.hours) * PRICE_PER_HOUR

    date_str = booking.date.strftime("%d %b %Y")
    start_str = start_dt.strftime("%I:%M %p")
    end_str = end_dt.strftime("%I:%M %p")
    price_str = f"₨{PRICE_PER_HOUR:,} / hour"
    total_str = f"₨{total_price:,}"

    # --- Customer email
    subject = "Confirm Your Booking"
    text_message = f"""Dear {booking.name},

Thank you for your booking. Please confirm your booking using the link below:

Confirm Link:
{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}

Booking Details:
Date: {date_str}
Start: {start_str}
End: {end_str}
Duration: {booking.hours} hour(s)
Total: {total_str}
"""

    html_message = f"""
    <html><body>
      <h2>Confirm Your Booking</h2>
      <p>Dear {booking.name},</p>
      <p>Click below to confirm your booking:</p>
      <a href="{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}">
        Confirm Booking
      </a>
      <p>Date: {date_str}<br>
      Time: {start_str} - {end_str}<br>
      Total: {total_str}</p>
    </body></html>
    """

    send_brevo_email(booking.email, subject, html_message, text_message)

    # --- Admin email
    admin_subject = f"New Booking Pending Confirmation - {booking.name}"
    admin_text = f"""
New Booking Alert!

Name: {booking.name}
Email: {booking.email}
Phone: {booking.phone}
Date: {date_str}
Start: {start_str}
End: {end_str}
Duration: {booking.hours} hour(s)
Total: {total_str}
"""

    admin_html = f"""
    <html><body>
      <h2>New Booking Alert</h2>
      <p><strong>Name:</strong> {booking.name}<br>
      <strong>Email:</strong> {booking.email}<br>
      <strong>Phone:</strong> {booking.phone}</p>
      <p><strong>Date:</strong> {date_str}<br>
      <strong>Start:</strong> {start_str}<br>
      <strong>End:</strong> {end_str}<br>
      <strong>Total:</strong> {total_str}</p>
    </body></html>
    """

    send_brevo_email(settings.ADMIN_EMAIL, admin_subject, admin_html, admin_text)

    return Response(
        {"message": "Booking created successfully. Confirmation email sent."},
        status=status.HTTP_201_CREATED
    )


@csrf_exempt
@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def get_booked_slots(request):
    date = request.GET.get('date')
    if not date:
        return Response({"error": "Date is required"}, status=400)

    bookings = Book.objects.filter(date=date).exclude(status="cancelled")
    blocked_slots = []
    for b in bookings:
        for h in range(int(b.hours)):
            blocked_slots.append(f"{(b.time.hour + h) % 24:02d}:00")

    return Response({"booked_slots": blocked_slots})


@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication, CsrfExemptSessionAuthentication])
def confirm_booking(request, booking_id, token):
    booking = get_object_or_404(Book, pk=booking_id)
    if booking.confirmation_token != token:
        return Response({"error": "Invalid or expired token"}, status=400)

    if booking.status == "cancelled":
        return Response({"error": "Booking is cancelled"}, status=400)

    if booking.confirmed_at:
        return Response({"message": "Booking already confirmed"}, status=200)

    booking.status = "confirmed"
    booking.confirmed_at = timezone.now()
    booking.confirmation_token = None
    booking.save(update_fields=["status", "confirmed_at", "confirmation_token", "updated_at"])

    return Response({"message": "Your booking has been confirmed"})


@api_view(['GET'])
@authentication_classes([CustomJWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    bookings = Book.objects.filter(user=request.user).order_by('-created_at')
    serializer = BookSerializer(bookings, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def cancel_booking(request, pk):
    try:
        booking = Book.objects.get(pk=pk, user=request.user)
    except Book.DoesNotExist:
        return Response({"error": "Booking not found"}, status=404)

    if booking.status in ["cancelled", "completed"]:
        return Response({"error": f"Cannot cancel a {booking.status} booking"}, status=400)

    start_dt = datetime.combine(booking.date, booking.time)
    if timezone.now() >= timezone.make_aware(start_dt, timezone.get_current_timezone()):
        return Response({"error": "Cannot cancel a past or ongoing booking"}, status=400)

    booking.status = "cancelled"
    if booking.payment_status == "paid":
        booking.payment_status = "refunded"
    booking.canceled_at = timezone.now()
    booking.save(update_fields=["status", "payment_status", "canceled_at", "updated_at"])

    date_str = booking.date.strftime("%d %b %Y")
    start_str = start_dt.strftime("%I:%M %p")
    total_str = f"₨{booking.total_price:,}"

    # --- User cancel email
    user_subject = "Booking Cancelled"
    user_text = f"Dear {booking.name}, your booking on {date_str} at {start_str} has been cancelled."
    user_html = f"<p>Dear {booking.name},<br>Your booking on {date_str} at {start_str} has been cancelled.<br>Total: {total_str}</p>"

    send_brevo_email(booking.email, user_subject, user_html, user_text)

    # --- Admin cancel email
    admin_subject = f"Booking Cancelled - {booking.name}"
    admin_text = f"Booking cancelled by {booking.name}, Date: {date_str}, Start: {start_str}"
    admin_html = f"<p>Booking cancelled by <b>{booking.name}</b> on {date_str} at {start_str}</p>"

    send_brevo_email(settings.ADMIN_EMAIL, admin_subject, admin_html, admin_text)

    return Response({"message": "Booking cancelled successfully"}, status=200)
