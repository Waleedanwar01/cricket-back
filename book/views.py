from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import secrets, requests
from .models import Book
from .serializers import BookSerializer
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


def styled_email_template(title, message, button_text=None, button_url=None, details=None, footer_text=None):
    """Reusable styled HTML email template"""
    details_html = ""
    if details:
        details_html = "<div class='details'>" + "".join(
            [f"<p><strong>{k}:</strong> {v}</p>" for k, v in details.items()]
        ) + "</div>"

    button_html = ""
    if button_text and button_url:
        button_html = f"""
        <a href="{button_url}" class="btn">{button_text}</a>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>{title}</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          background-color: #f8f9fa;
          margin: 0;
          padding: 0;
        }}
        .container {{
          max-width: 600px;
          margin: 20px auto;
          background: #ffffff;
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          padding: 20px;
        }}
        h2 {{
          color: #2c3e50;
          text-align: center;
        }}
        p {{
          color: #555;
          line-height: 1.5;
        }}
        .details {{
          margin: 20px 0;
          padding: 15px;
          background: #f4f6f8;
          border-radius: 8px;
        }}
        .btn {{
          display: inline-block;
          background: #28a745;
          color: #fff !important;
          text-decoration: none;
          padding: 12px 20px;
          border-radius: 6px;
          font-weight: bold;
          text-align: center;
          margin: 20px 0;
        }}
        .footer {{
          font-size: 12px;
          color: #aaa;
          text-align: center;
          margin-top: 20px;
        }}
      </style>
    </head>
    <body>
      <div class="container">
        <h2>{title}</h2>
        <p>{message}</p>
        {button_html}
        {details_html}
        <div class="footer">{footer_text or f"&copy; {datetime.now().year} Cricket Court"}</div>
      </div>
    </body>
    </html>
    """


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
    total_str = f"₨{total_price:,}"

    # --- Customer email
    subject = "Confirm Your Booking"
    confirm_url = f"{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}"

    text_message = f"""
Dear {booking.name},

Thank you for your booking. Please confirm your booking using the link below:

{confirm_url}

Booking Details:
Date: {date_str}
Time: {start_str} - {end_str}
Duration: {booking.hours} hour(s)
Total: {total_str}
"""

    html_message = styled_email_template(
        title="Confirm Your Booking",
        message=f"Dear {booking.name},<br>Thank you for your booking. Please confirm your booking below.",
        button_text="Confirm Booking",
        button_url=confirm_url,
        details={
            "Date": date_str,
            "Time": f"{start_str} - {end_str}",
            "Duration": f"{booking.hours} hour(s)",
            "Total": total_str,
        }
    )

    send_brevo_email(booking.email, subject, html_message, text_message)

    # --- Admin email
    admin_subject = f"New Booking Pending Confirmation - {booking.name}"

    admin_html = styled_email_template(
        title="New Booking Alert",
        message=f"A new booking has been made by <b>{booking.name}</b>. Pending confirmation.",
        details={
            "Name": booking.name,
            "Email": booking.email,
            "Phone": booking.phone,
            "Date": date_str,
            "Time": f"{start_str} - {end_str}",
            "Duration": f"{booking.hours} hour(s)",
            "Total": total_str,
        }
    )

    admin_text = f"""
New Booking Alert!

Name: {booking.name}
Email: {booking.email}
Phone: {booking.phone}
Date: {date_str}
Time: {start_str} - {end_str}
Duration: {booking.hours} hour(s)
Total: {total_str}
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

    user_html = styled_email_template(
        title="Booking Cancelled",
        message=f"Dear {booking.name},<br>Your booking has been cancelled.",
        details={
            "Date": date_str,
            "Time": start_str,
            "Total Refund": total_str,
        }
    )

    send_brevo_email(booking.email, user_subject, user_html, user_text)

    # --- Admin cancel email
    admin_subject = f"Booking Cancelled - {booking.name}"
    admin_text = f"Booking cancelled by {booking.name}, Date: {date_str}, Start: {start_str}"

    admin_html = styled_email_template(
        title="Booking Cancelled",
        message=f"Booking cancelled by <b>{booking.name}</b>.",
        details={
            "Date": date_str,
            "Time": start_str,
            "Total Refund": total_str,
        }
    )

    send_brevo_email(settings.ADMIN_EMAIL, admin_subject, admin_html, admin_text)

    return Response({"message": "Booking cancelled successfully"}, status=200)
