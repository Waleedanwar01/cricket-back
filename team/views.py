from .models import Team
from django.http import JsonResponse
# Create your views here.
def getTeam(request):
    if request.method == "GET":
        teamMember = Team.objects.all().values("id", "name", "rank", "image", "linkdin", "twitter", "facebook")
        return JsonResponse(list(teamMember), safe=False)
    