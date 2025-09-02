from rest_framework_simplejwt.tokens import RefreshToken
from urllib.parse import urlencode
from django.shortcuts import redirect

def generate_jwt(backend, user, response, *args, **kwargs):
    refresh = RefreshToken.for_user(user)
    response['jwt_access'] = str(refresh.access_token)
    response['jwt_refresh'] = str(refresh)
    return response

def get_jwt_tokens_for_redirect(backend, user, response, *args, **kwargs):
    """
    Get JWT tokens for social auth users and add them to the redirect URL
    """
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)
    
    # Get the redirect URL from the request
    redirect_url = kwargs.get('redirect_url') or backend.strategy.session_get('next', None)
    
    # If there's no redirect URL, use the default
    if not redirect_url:
        return
    
    # Add tokens to the redirect URL
    params = {
        'access': access_token,
        'refresh': refresh_token
    }
    
    # Check if the URL already has query parameters
    if '?' in redirect_url:
        redirect_url = f"{redirect_url}&{urlencode(params)}"
    else:
        redirect_url = f"{redirect_url}?{urlencode(params)}"
    
    # Store the updated redirect URL in the session
    backend.strategy.session_set('next', redirect_url)
    
    return {'redirect_url': redirect_url}
