from django.urls import path
from . import views

urlpatterns = [
    path('tournaments/', views.my_tournaments, name='my-tournaments'),
    path('tournaments/create/', views.create_tournament, name='create-tournament'),
    path('tournaments/active/', views.active_tournaments, name='active-tournaments'),
    path('tournaments/all/', views.all_tournaments, name='all-tournaments'),
    path('tournaments/<int:pk>/confirm/', views.admin_confirm_tournament, name='admin-confirm-tournament'),
    path('tournaments/<int:pk>/cancel/', views.cancel_tournament, name='cancel-tournament'),
    path('tournaments/<int:tournament_id>/entries/', views.create_team_entry, name='create-team-entry'),
    path('entries/<int:entry_id>/cancel/', views.cancel_team_entry, name='cancel-team-entry'),
    path('my/entries/', views.my_entries, name='my-entries'),
]


