from django.contrib import admin
from .models import Team
# Register your models here.

@admin.register(Team)
class AdminTeam(admin.ModelAdmin):
    list_display = ('name', 'rank', 'linkdin', 'facebook', 'twitter')
    search_fields = ('name', 'rank')
