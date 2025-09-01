from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.conf import settings


@csrf_exempt
def contactUs(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name")
            email = data.get("email")
            message = data.get("message")

            # Check if any field is missing
            if not name or not email or not message:
                return JsonResponse({"error": "All fields are required!"}, status=400)

            # Send email
            send_mail(
                subject=f"New Contact Message from {name}",
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=["waleeddogare@gmail.com"],
                fail_silently=False,
            )

            return JsonResponse({"message": "Message sent successfully!"})

        except Exception as e:
            print("Error sending email:", e)
            return JsonResponse({"error": "Failed to send email"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
