from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Tournament, TeamEntry
from .serializers import TournamentSerializer, TeamEntrySerializer
from django.utils import timezone
from datetime import date
from django.db.models import Q
from book.authentication import CsrfExemptSessionAuthentication

HOURLY_RATE = 1800

@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def create_tournament(request):
    # Debug logs
    print("User:", request.user)
    print("Authenticated:", request.user.is_authenticated)
    print("Auth headers:", request.META.get('HTTP_AUTHORIZATION'))
    
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = TournamentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    tournament = serializer.save(holder=request.user, daily_hours=2)  # force 2 hours per day

    # Notify holder and admin
    subject = "Tournament Request Received"
    text = (
        f"Dear {request.user.username},\n\n"
        f"Your tournament request '{tournament.name}' has been received.\n"
        f"Court charge is PKR {HOURLY_RATE} per hour. Daily slot is 2 hours.\n"
        f"Status: {tournament.status}.\n\nRegards, Cricket Court"
    )
    send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [request.user.email], fail_silently=False)

    admin_subject = f"New Tournament Request - {tournament.name}"
    admin_text = (
        f"Holder: {request.user.username} ({request.user.email})\n"
        f"Date: {tournament.start_date} {tournament.daily_start_time}\n"
        f"Max teams: {tournament.max_teams}\n"
        f"Please review and book the slot if available."
    )
    send_mail(admin_subject, admin_text, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=False)

    return Response({
        "message": "Tournament request submitted. You'll get email once booked.",
        "data": TournamentSerializer(tournament).data
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def my_tournaments(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
    items = Tournament.objects.filter(holder=request.user).order_by('-created_at')
    return Response(TournamentSerializer(items, many=True).data)


@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAdminUser])
def admin_confirm_tournament(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        t = Tournament.objects.get(pk=pk)
    except Tournament.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    t.status = 'confirmed'
    t.save(update_fields=['status', 'updated_at'])
    
    # Email holder
    send_mail(
        "Tournament Confirmed",
        f"Your tournament '{t.name}' has been confirmed.",
        settings.DEFAULT_FROM_EMAIL,
        [t.holder.email],
        fail_silently=False,
    )
    
    return Response({"message": "Tournament confirmed"})


@api_view(['GET'])
def active_tournaments(request):
    today = date.today()
    qs = Tournament.objects.filter(status__in=['confirmed', 'booked'], registration_deadline__gte=today)
    return Response(TournamentSerializer(qs, many=True).data)


@api_view(['GET'])
def all_tournaments(request):
    qs = Tournament.objects.all().order_by('-created_at')
    return Response(TournamentSerializer(qs, many=True).data)


@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def cancel_tournament(request, pk):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        t = Tournament.objects.get(pk=pk)
    except Tournament.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    # Only holder or admin
    if not (request.user.is_staff or request.user == t.holder):
        return Response({"error": "Not allowed"}, status=403)

    if t.status == 'cancelled':
        return Response({"message": "Already cancelled"})

    t.status = 'cancelled'
    t.save(update_fields=['status', 'updated_at'])

    # Notify holder and admin
    send_mail(
        "Tournament Cancelled",
        f"Your tournament '{t.name}' has been cancelled.",
        settings.DEFAULT_FROM_EMAIL,
        [t.holder.email, settings.ADMIN_EMAIL],
        fail_silently=False,
    )

    return Response({"message": "Tournament cancelled"})


@api_view(['POST', 'OPTIONS'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def create_team_entry(request, tournament_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        t = Tournament.objects.get(pk=tournament_id)
    except Tournament.DoesNotExist:
        return Response({"error": "Tournament not found"}, status=404)

    # Check registration window
    if t.registration_deadline < date.today():
        return Response({"error": "Registration closed"}, status=400)

    # Check teams count limit
    current = t.entries.exclude(status='cancelled').count()
    if current >= t.max_teams:
        return Response({"error": "Team limit reached"}, status=400)

    serializer = TeamEntrySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    entry = TeamEntry.objects.create(
        tournament=t,
        captain=request.user,
        team_name=serializer.validated_data['team_name'],
        contact_phone=serializer.validated_data.get('contact_phone', ''),
        status='approved'  # auto-approve for now
    )

    # Notify captain (HTML)
    captain_subject = "Team Entry Confirmed"
    captain_text = (
        f"Your team '{entry.team_name}' has been registered in tournament '{t.name}'.\n"
        f"Start: {t.start_date} {t.daily_start_time}\n"
        f"Entry Fee: PKR {t.entry_fee}\n"
    )
    captain_html = f"""
    <html>
      <body style=\"font-family:Arial,Helvetica,sans-serif;background:#f4f4f4;padding:20px;\">
        <div style=\"max-width:600px;margin:0 auto;background:#ffffff;padding:20px;border-radius:10px;\">
          <h2 style=\"color:#065f46;\">Team Entry Confirmed</h2>
          <p>Dear {request.user.username},</p>
          <p>Your team <strong>{entry.team_name}</strong> has been registered in <strong>{t.name}</strong>.</p>
          <table style=\"width:100%;border-collapse:collapse;margin-top:10px;\">
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Start</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{t.start_date} {t.daily_start_time}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Entry Fee</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">PKR {t.entry_fee}</td></tr>
          </table>
          <p style=\"margin-top:15px;\">Good luck!</p>
          <p>Regards,<br>Cricket Court</p>
        </div>
      </body>
    </html>
    """
    send_mail(captain_subject, captain_text, settings.DEFAULT_FROM_EMAIL, [request.user.email], html_message=captain_html, fail_silently=False)

    # Notify holder (HTML)
    holder_subject = "New Team Entry Received"
    holder_text = (
        f"A new team has entered your tournament.\n\n"
        f"Tournament: {t.name}\nTeam: {entry.team_name}\nCaptain: {request.user.username} ({request.user.email})\n"
        f"Captain Phone: {entry.contact_phone or 'N/A'}\n"
    )
    holder_html = f"""
    <html>
      <body style=\"font-family:Arial,Helvetica,sans-serif;background:#f4f4f4;padding:20px;\">
        <div style=\"max-width:600px;margin:0 auto;background:#ffffff;padding:20px;border-radius:10px;\">
          <h2 style=\"color:#1d4ed8;\">New Team Entry</h2>
          <p>A new team has registered for your tournament:</p>
          <table style=\"width:100%;border-collapse:collapse;margin-top:10px;\">
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Tournament</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{t.name}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Team</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{entry.team_name}</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Captain</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{request.user.username} ({request.user.email})</td></tr>
            <tr><td style=\"padding:8px;border:1px solid #ddd;\"><strong>Captain Phone</strong></td><td style=\"padding:8px;border:1px solid #ddd;\">{entry.contact_phone or 'N/A'}</td></tr>
          </table>
          <p style=\"margin-top:15px;\">You now have {t.entries.exclude(status='cancelled').count()} team(s) registered.</p>
          <p>Regards,<br>Cricket Court</p>
        </div>
      </body>
    </html>
    """
    send_mail(holder_subject, holder_text, settings.DEFAULT_FROM_EMAIL, [t.holder.email, settings.ADMIN_EMAIL], html_message=holder_html, fail_silently=False)

    return Response({"message": "Team entry created", "data": TeamEntrySerializer(entry).data}, status=201)


@api_view(['POST'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def cancel_team_entry(request, entry_id):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        entry = TeamEntry.objects.select_related('tournament').get(pk=entry_id)
    except TeamEntry.DoesNotExist:
        return Response({"error": "Entry not found"}, status=404)

    # Captain or admin can cancel
    if not (request.user.is_staff or request.user == entry.captain):
        return Response({"error": "Not allowed"}, status=403)

    entry.status = 'cancelled'
    entry.save(update_fields=['status', 'updated_at'])

    # Emails
    send_mail(
        "Team Entry Cancelled",
        f"Team '{entry.team_name}' entry cancelled for tournament '{entry.tournament.name}'.",
        settings.DEFAULT_FROM_EMAIL,
        [entry.captain.email, settings.ADMIN_EMAIL],
        fail_silently=False,
    )

    return Response({"message": "Entry cancelled"})


@api_view(['GET'])
@authentication_classes([JWTAuthentication, CsrfExemptSessionAuthentication])
@permission_classes([IsAuthenticated])
def my_entries(request):
    if not request.user.is_authenticated:
        return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
    entries = TeamEntry.objects.select_related('tournament').filter(captain=request.user).order_by('-created_at')
    return Response(TeamEntrySerializer(entries, many=True).data)