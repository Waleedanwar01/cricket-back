from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests
from django.conf import settings

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

def send_brevo_email(to_email, subject, html_content, text_content=None):
    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }
    payload = {
        "sender": {"name": "Cricket Court", "email": settings.DEFAULT_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content or subject,
    }
    response = requests.post(BREVO_API_URL, headers=headers, json=payload)
    response.raise_for_status()  # Raise error if API fails
    return response.json()


@csrf_exempt
def contactUs(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        name = data.get("name")
        email = data.get("email")
        message = data.get("message")

        if not name or not email or not message:
            return JsonResponse({"error": "All fields are required!"}, status=400)

        subject = f"New Contact Message from {name}"
        html_content = f"""
            <p><strong>From:</strong> {name} ({email})</p>
            <p><strong>Message:</strong></p>
            <p>{message}</p>
        """

        send_brevo_email(settings.ADMIN_EMAIL, subject, html_content, message)

        return JsonResponse({"message": "Message sent successfully!"})

    except requests.exceptions.RequestException as e:
        print("Brevo API error:", e)
        return JsonResponse({"error": "Failed to send email via Brevo"}, status=500)
    except Exception as e:
        print("Unexpected error:", e)
        return JsonResponse({"error": "Failed to send email"}, status=500)
