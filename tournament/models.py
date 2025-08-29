from django.db import models
from django.contrib.auth.models import User


class Tournament(models.Model):
    HOLDER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("booked", "Booked"),
        ("cancelled", "Cancelled"),
    ]

    holder = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tournaments")
    name = models.CharField(max_length=150)
    game = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    start_date = models.DateField()
    daily_start_time = models.TimeField()
    daily_hours = models.PositiveIntegerField(default=2)  # fixed 2 hours per day
    entry_fee = models.PositiveIntegerField()
    registration_deadline = models.DateField()
    holder_phone = models.CharField(max_length=20, blank=True)
    prize_money = models.PositiveIntegerField(default=0)
    max_teams = models.PositiveIntegerField()
    max_players_per_team = models.PositiveIntegerField()
    max_overs = models.PositiveIntegerField()
    description = models.TextField()

    status = models.CharField(max_length=20, choices=HOLDER_STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.holder.username})"


class TeamEntry(models.Model):
    ENTRY_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="entries")
    captain = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_entries")
    team_name = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=ENTRY_STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.team_name} - {self.tournament.name}"

