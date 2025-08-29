from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings

from .models import Tournament, TeamEntry


class TeamEntryInline(admin.TabularInline):
    model = TeamEntry
    fields = ("team_name", "captain", "contact_phone", "status", "created_at")
    readonly_fields = ("created_at",)
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "holder",
        "start_date",
        "daily_start_time",
        "registration_deadline",
        "max_teams",
        "status",
        "created_at",
    )
    list_filter = ("status", "start_date", "registration_deadline")
    search_fields = ("name", "holder__username", "holder__email")
    inlines = [TeamEntryInline]

    @admin.action(description="Mark selected tournaments as Confirmed and notify holder")
    def mark_confirmed(self, request, queryset):
        updated = queryset.update(status="confirmed")
        for t in queryset:
            try:
                send_mail(
                    "Tournament Confirmed",
                    f"Your tournament '{t.name}' has been confirmed.",
                    settings.DEFAULT_FROM_EMAIL,
                    [t.holder.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        self.message_user(request, f"{updated} tournament(s) marked as confirmed.")

    @admin.action(description="Mark selected tournaments as Booked")
    def mark_booked(self, request, queryset):
        updated = queryset.update(status="booked")
        self.message_user(request, f"{updated} tournament(s) marked as booked.")

    @admin.action(description="Mark selected tournaments as Cancelled")
    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status="cancelled")
        self.message_user(request, f"{updated} tournament(s) marked as cancelled.")

    actions = ("mark_confirmed", "mark_booked", "mark_cancelled")


@admin.register(TeamEntry)
class TeamEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "team_name", "tournament", "captain", "status", "created_at")
    list_filter = ("status", "tournament")
    search_fields = ("team_name", "captain__username", "tournament__name")

    @admin.action(description="Approve selected entries")
    def approve_entries(self, request, queryset):
        updated = queryset.update(status="approved")
        self.message_user(request, f"{updated} entry(ies) approved.")

    @admin.action(description="Cancel selected entries and notify captain")
    def cancel_entries(self, request, queryset):
        updated = 0
        for entry in queryset:
            if entry.status != "cancelled":
                entry.status = "cancelled"
                entry.save(update_fields=["status", "updated_at"])
                updated += 1
                try:
                    send_mail(
                        "Team Entry Cancelled",
                        f"Team '{entry.team_name}' entry cancelled for tournament '{entry.tournament.name}'.",
                        settings.DEFAULT_FROM_EMAIL,
                        [entry.captain.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
        self.message_user(request, f"{updated} entry(ies) cancelled.")

    actions = ("approve_entries", "cancel_entries")


