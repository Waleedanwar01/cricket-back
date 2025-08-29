# accounts/views.py
import json
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.middleware.csrf import get_token
from functools import wraps

User = get_user_model()

@csrf_exempt
def signup_api(request):
    if request.user.is_authenticated:
     return JsonResponse({"message": "Already logged in"}, status=200)
        
    else: 
     if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    data = json.loads(request.body)
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if User.objects.filter(username=username).exists():
        return JsonResponse({"error": "Username already exists"}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({"error": "Email already registered"}, status=400)
    user = User.objects.create_user(username=username, email=email, password=password)
    return JsonResponse({"message": "User created successfully"})
@csrf_exempt
def login_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return JsonResponse({"error": "Username and password required"}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=400)
    else:
        login(request, user)
        return JsonResponse({
            "message": "Logged in successfully",
            "user": {
                "username": user.username,
                "email": user.email,
            }
        }, status=200)

@login_required
def logout_api(request):
    logout(request)
    return JsonResponse({"message": "Logged out successfully"})

def login_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required_json
def me(request):
    return JsonResponse({
        "id": request.user.id,
        "username": request.user.username,
        "email": request.user.email,
    })

@csrf_exempt
def get_csrf_token(request):
    """Get CSRF token for API requests"""
    return JsonResponse({
        'csrfToken': get_token(request)
    })