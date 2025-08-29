from rest_framework import serializers
from .models import Tournament, TeamEntry


class TournamentSerializer(serializers.ModelSerializer):
    entries_count = serializers.SerializerMethodField()
    remaining_spots = serializers.SerializerMethodField()
    class Meta:
        model = Tournament
        fields = [
            'id', 'name', 'game', 'location', 'start_date', 'daily_start_time', 'daily_hours',
            'entry_fee', 'registration_deadline', 'holder_phone', 'prize_money', 'max_teams', 'max_players_per_team', 'max_overs', 'description',
            'status', 'created_at', 'updated_at', 'entries_count', 'remaining_spots'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']

    def get_entries_count(self, obj):
        return obj.entries.exclude(status='cancelled').count()

    def get_remaining_spots(self, obj):
        used = self.get_entries_count(obj)
        remaining = max(int(obj.max_teams) - int(used), 0)
        return remaining


class TeamEntrySerializer(serializers.ModelSerializer):
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    entry_fee = serializers.IntegerField(source='tournament.entry_fee', read_only=True)
    start_date = serializers.DateField(source='tournament.start_date', read_only=True)
    daily_start_time = serializers.TimeField(source='tournament.daily_start_time', read_only=True)

    class Meta:
        model = TeamEntry
        fields = [
            'id', 'tournament', 'tournament_name', 'entry_fee', 'start_date', 'daily_start_time',
            'team_name', 'contact_phone', 'status', 'created_at'
        ]
        read_only_fields = ['status', 'created_at', 'tournament', 'tournament_name', 'entry_fee', 'start_date', 'daily_start_time']


