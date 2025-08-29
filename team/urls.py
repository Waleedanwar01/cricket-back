
from django.urls import path
from . import views   # ✅ Import views from the same app

urlpatterns = [
    path('team/', views.getTeam, name='getTeam')
   
]
