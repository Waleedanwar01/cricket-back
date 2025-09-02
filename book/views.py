from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import secrets
import requests
from .models import Book
from .serializers import BookSerializer
from datetime import timedelta, datetime
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from .authentication import CsrfExemptSessionAuthentication, CustomJWTAuthentication
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404

PRICE_PER_HOUR = 1500
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_brevo_email(to_email, subject, html_content, text_content=None):
    """Helper to send email using Brevo API"""
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
    try:
        response = requests.post(BREVO_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print("Brevo email error:", e)
        return False


def check_booking_availability(date, start_time, hours):
    """Check if the requested time slots are available"""
    start_hour = start_time.hour
    requested_slots = [f"{(start_hour + h) % 24:02d}:00" for h in range(hours)]

    existing_bookings = Book.objects.filter(date=date).exclude(status="cancelled")
    conflicting_slots = []

    for booking in existing_bookings:
        booking_start = booking.time.hour
        booking_end = (booking_start + booking.hours) % 24

        for slot in requested_slots:
            slot_hour = int(slot.split(':')[0])

            if booking_start < booking_end:  # Normal booking
                if booking_start <= slot_hour < booking_end:
                    conflicting_slots.append(slot)
            else:  # Cross midnight
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

    booking_data = serializer.validated_data
    date = booking_data['date']
    time = booking_data['time']
    hours = int(booking_data['hours'])

    # Check conflicts
    conflicting_slots = check_booking_availability(date, time, hours)
    if conflicting_slots:
        return Response(
            {
                "error": "Time slot not available",
                "conflicting_slots": conflicting_slots,
                "message": f"The following hours are already booked: {', '.join(conflicting_slots)}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Save booking
    booking = serializer.save(user=request.user)
    booking.confirmation_token = secrets.token_urlsafe(32)
    booking.save(update_fields=["confirmation_token", "updated_at"])

    # Times & pricing
    start_dt = datetime.combine(booking.date, booking.time)
    end_dt = start_dt + timedelta(hours=int(booking.hours))
    total_price = int(booking.hours) * PRICE_PER_HOUR

    date_str = booking.date.strftime("%d %b %Y")
    start_str = start_dt.strftime("%I:%M %p")
    end_str = end_dt.strftime("%I:%M %p")
    price_str = f"₨{PRICE_PER_HOUR:,} / hour"
    total_str = f"₨{total_price:,}"

    # ----------------- CUSTOMER EMAIL -----------------
    subject = "Confirm Your Booking"
    text_message = f"""Dear {booking.name},

Thank you for your booking. Please confirm your booking:

{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}

Booking Details:
• Date: {date_str}
• Time: {start_str} - {end_str}
• Duration: {booking.hours} hours
• Price: {price_str}
• Total: {total_str}
• Phone: {booking.phone}
"""

    html_message = f"""
    <html>
      <body>
        <h2>Confirm Your Booking</h2>
        <p>Dear {booking.name},</p>
        <p>Please confirm your booking:</p>
        <a href="{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}">Confirm Booking</a>
        <p><strong>Date:</strong> {date_str}<br>
        <strong>Start:</strong> {start_str}<br>
        <strong>End:</strong> {end_str}<br>
        <strong>Duration:</strong> {booking.hours} hours<br>
        <strong>Total:</strong> {total_str}<br>
        <strong>Phone:</strong> {booking.phone}</p>
      </body>
    </html>
    """
    send_brevo_email(booking.email, subject, html_message, text_message)

    # ----------------- ADMIN EMAIL -----------------
    admin_subject = f"New Booking Pending Confirmation - {booking.name}"
    admin_text = f"New booking from {booking.name} ({booking.email}) on {date_str} at {start_str} for {booking.hours} hours. Total {total_str}."
    admin_html = f"""
    <html>
      <body>
        <h2>New Booking Pending Confirmation</h2>
        <p>Name: {booking.name}<br>Email: {booking.email}<br>Phone: {booking.phone}</p>
        <p>Date: {date_str}<br>Start: {start_str}<br>End: {end_str}<br>Duration: {booking.hours} hours<br>Total: {total_str}</p>
      </body>
    </html>
    """
    send_brevo_email(settings.ADMIN_EMAIL, admin_subject, admin_html, admin_text)

    return Response(
        {
            "message": "Booking created successfully. Confirmation email sent.",
            "data": BookSerializer(booking).data,
            "calculated": {"end_time": end_str, "total": total_price}
        },
        status=status.HTTP_201_CREATED
    )
