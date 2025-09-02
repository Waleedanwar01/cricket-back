from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from datetime import datetime, timedelta
import secrets
from .models import Book
from .serializers import BookSerializer
from datetime import timedelta, datetime, time as dt_time
from django.contrib.auth.decorators import login_required
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from .authentication import CsrfExemptSessionAuthentication, CustomJWTAuthentication
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404

PRICE_PER_HOUR = 1500


def check_booking_availability(date, start_time, hours):
    """
    Check if the requested time slots are available
    Returns list of conflicting slots if any
    """
    start_hour = start_time.hour
    requested_slots = []

    # Generate all slots for the requested booking
    for h in range(hours):
        slot_hour = (start_hour + h) % 24
        requested_slots.append(f"{slot_hour:02d}:00")

    # Get existing bookings for the date
    existing_bookings = Book.objects.filter(date=date).exclude(status="cancelled")
    conflicting_slots = []

    for booking in existing_bookings:
        booking_start = booking.time.hour
        booking_end = (booking_start + booking.hours) % 24

        # Check each requested slot against this booking
        for slot in requested_slots:
            slot_hour = int(slot.split(':')[0])

            if booking_start < booking_end:  # Normal booking (same day)
                if booking_start <= slot_hour < booking_end:
                    conflicting_slots.append(slot)
            else:  # Booking crosses midnight
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

    # Check for booking conflicts before saving
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
 # # Save booking with logged-in user
    booking = serializer.save(user=request.user)  # only save once
    # Keep status pending by default, generate confirmation token
    booking.confirmation_token = secrets.token_urlsafe(32)
    booking.save(update_fields=["confirmation_token", "updated_at"])
    

    # Calculate end time and totals
    start_dt = datetime.combine(booking.date, booking.time)
    end_dt = start_dt + timedelta(hours=int(booking.hours))
    total_price = int(booking.hours) * PRICE_PER_HOUR

    # Format strings for email
    date_str = booking.date.strftime("%d %b %Y")
    start_str = start_dt.strftime("%I:%M %p")
    end_str = end_dt.strftime("%I:%M %p")
    price_str = f"₨{PRICE_PER_HOUR:,} / hour"
    total_str = f"₨{total_price:,}"

    # Email content
    subject = "Confirm Your Booking"
    text_message = f"""Dear {booking.name},

Thank you for your booking. Please confirm your booking using the link below:

Confirm Link:
{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}

Booking Details (pending until confirmed):
• Date: {date_str}
• Start Time: {start_str}
• End Time: {end_str}
• Duration: {booking.hours} hour(s)
• Price per Hour: {price_str}
• Total: {total_str}
• Phone: {booking.phone}

We will contact you soon for further updates.

Regards,
Your Company Team
"""

    html_message = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;background:#f4f4f4;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;padding:20px;border-radius:10px;">
          <h2 style="color:#065f46;">Confirm Your Booking</h2>
          <p>Dear {booking.name},</p>
          <p>Thank you for your booking. Please confirm your booking to finalize it:</p>
          <p><a href="{settings.FRONTEND_CONFIRM_URL}?id={booking.id}&token={booking.confirmation_token}" style="display:inline-block;background:#065f46;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;">Confirm Booking</a></p>
          <table style="width:100%;border-collapse:collapse;margin-top:15px;">
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Date</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{date_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Start Time</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{start_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>End Time</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{end_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Duration</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{booking.hours} hour(s)</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Price per Hour</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{price_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Total</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{total_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Phone</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{booking.phone}</td>
            </tr>
          </table>
          <p style="margin-top:15px;">Note: Your booking status is <strong>pending</strong> until you confirm via email.</p>
          <p>Regards,<br>Cricket Court</p>
        </div>
      </body>
    </html>
    """

    # Send email to customer
    send_mail(
        subject=subject,
        message=text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.email],
        html_message=html_message,
        fail_silently=False,
    )

    # Send notification email to admin
    admin_subject = f"New Booking Pending Confirmation - {booking.name}"
    admin_text_message = f"""New Booking Alert!

A new booking has been received:

Customer Details:
• Name: {booking.name}
• Email: {booking.email}
• Phone: {booking.phone}

Booking Details:
• Date: {date_str}
• Start Time: {start_str}
• End Time: {end_str}
• Duration: {booking.hours} hour(s)
• Total Amount: {total_str}

Please prepare the court for the scheduled time.

Regards,
Cricket Court System
"""

    admin_html_message = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;background:#f4f4f4;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;padding:20px;border-radius:10px;">
          <h2 style="color:#dc2626;">🏏 New Booking Pending Confirmation</h2>
          <p>A new booking has been received and is pending user confirmation:</p>
          
          <h3 style="color:#065f46;">Customer Details:</h3>
          <table style="width:100%;border-collapse:collapse;margin-top:10px;">
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Name</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{booking.name}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Email</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{booking.email}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Phone</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{booking.phone}</td>
            </tr>
          </table>
          
          <h3 style="color:#065f46;margin-top:20px;">Booking Details:</h3>
          <table style="width:100%;border-collapse:collapse;margin-top:10px;">
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Date</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{date_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Start Time</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{start_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>End Time</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{end_str}</td>
            </tr>
            <tr>
              <td style="padding:8px;border:1px solid #ddd;"><strong>Duration</strong></td>
              <td style="padding:8px;border:1px solid #ddd;">{booking.hours} hour(s)</td>
            </tr>
            <tr style="background-color:#f0fdf4;">
              <td style="padding:8px;border:1px solid #ddd;"><strong>Total Amount</strong></td>
              <td style="padding:8px;border:1px solid #ddd;font-weight:bold;color:#065f46;">{total_str}</td>
            </tr>
          </table>
          
          <p style="margin-top:20px;padding:15px;background-color:#fef3c7;border-radius:5px;">
            <strong>Action Required:</strong> Please prepare the court for the scheduled time and contact the customer if needed.
          </p>
          
          <p>Regards,<br>Cricket Court System</p>
        </div>
      </body>
    </html>
    """

    # Send admin notification
    send_mail(
        subject=admin_subject,
        message=admin_text_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],  # Admin email from settings
        html_message=admin_html_message,
        fail_silently=False,
    )

    return Response(
        {
            "message": "Booking created successfully. Confirmation email sent.",
            "data": BookSerializer(booking).data,
            "calculated": {
                "end_time": end_str,
                "total": total_price
            }
        },
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
        start_hour = b.time.hour
        for h in range(int(b.hours)):
            slot_hour = (start_hour + h) % 24
            blocked_slots.append(f"{slot_hour:02d}:00")

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
    """List all bookings for the logged-in user"""
    bookings = Book.objects.filter(user=request.user).order_by('-created_at')
    serializer = BookSerializer(bookings, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([CustomJWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def cancel_booking(request, pk):
    """Allow a user to cancel their future booking"""
    try:
        booking = Book.objects.get(pk=pk, user=request.user)
    except Book.DoesNotExist:
        return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

    if booking.status in ["cancelled", "completed"]:
        return Response({"error": f"Cannot cancel a {booking.status} booking"}, status=status.HTTP_400_BAD_REQUEST)

    start_dt = datetime.combine(booking.date, booking.time)
    # Disallow cancel if start time has passed
    if timezone.now() >= timezone.make_aware(start_dt, timezone.get_current_timezone()):
        return Response({"error": "Cannot cancel a past or ongoing booking"}, status=status.HTTP_400_BAD_REQUEST)

    # Update status and payment status
    booking.status = "cancelled"
    if booking.payment_status == "paid":
        booking.payment_status = "refunded"
    booking.canceled_at = timezone.now()
    booking.save(update_fields=["status", "payment_status", "canceled_at", "updated_at"])

    # Email notifications
    date_str = booking.date.strftime("%d %b %Y")
    start_str = start_dt.strftime("%I:%M %p")
    total_str = f"₨{booking.total_price:,}"

    # User email
    user_subject = "Booking Cancelled"
    user_text = (
        f"Dear {booking.name},\n\n"
        f"Your booking on {date_str} at {start_str} for {booking.hours} hour(s) has been cancelled.\n"
        f"Total: {total_str}\n\nRegards,\nCricket Court"
    )
    user_html = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;background:#f4f4f4;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;padding:20px;border-radius:10px;">
          <h2 style="color:#b91c1c;">Booking Cancelled</h2>
          <p>Dear {booking.name},</p>
          <p>Your booking has been cancelled.</p>
          <table style="width:100%;border-collapse:collapse;margin-top:15px;">
            <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Date</strong></td><td style="padding:8px;border:1px solid #ddd;">{date_str}</td></tr>
            <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Start Time</strong></td><td style="padding:8px;border:1px solid #ddd;">{start_str}</td></tr>
            <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Duration</strong></td><td style="padding:8px;border:1px solid #ddd;">{booking.hours} hour(s)</td></tr>
            <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Total</strong></td><td style="padding:8px;border:1px solid #ddd;">{total_str}</td></tr>
            <tr><td style="padding:8px;border:1px solid #ddd;"><strong>Status</strong></td><td style="padding:8px;border:1px solid #ddd;">Cancelled</td></tr>
          </table>
          <p style="margin-top:15px;">If this was a mistake, please create a new booking.</p>
          <p>Regards,<br>Cricket Court</p>
        </div>
      </body>
    </html>
    """

    send_mail(
        subject=user_subject,
        message=user_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.email],
        html_message=user_html,
        fail_silently=False,
    )

    # Admin email
    admin_subject = f"Booking Cancelled - {booking.name}"
    admin_text = (
        f"Booking cancelled by user.\n\n"
        f"Name: {booking.name}\nEmail: {booking.email}\nPhone: {booking.phone}\n"
        f"Date: {date_str}\nStart: {start_str}\nHours: {booking.hours}\n"
        f"Total: {total_str}\nStatus: Cancelled\n"
    )
    admin_html = f"""
    <html>
      <body style="font-family:Arial,Helvetica,sans-serif;background:#f4f4f4;padding:20px;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;padding:20px;border-radius:10px;">
          <h2 style="color:#b91c1c;">User Cancelled Booking</h2>
          <table style=\"width:100%;border-collapse:collapse;margin-top:10px;\">
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Name</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{booking.name}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Email</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{booking.email}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Phone</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{booking.phone}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Date</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{date_str}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Start</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{start_str}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Hours</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{booking.hours}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Total</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{total_str}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Status</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">Cancelled</td></tr>
          </table>
          <p>Regards,<br>Cricket Court System</p>
        </div>
      </body>
    </html>
    """

    send_mail(
        subject=admin_subject,
        message=admin_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        html_message=admin_html,
        fail_silently=False,
    )

    return Response({"message": "Booking cancelled successfully"}, status=status.HTTP_200_OK)
