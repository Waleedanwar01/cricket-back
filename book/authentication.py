from rest_framework.authentication import SessionAuthentication, BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication scheme that doesn't enforce CSRF.
    """
    def enforce_csrf(self, request):
        return  # Skip CSRF check 

class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that handles both header and cookie authentication.
    """
    def authenticate(self, request):
        try:
            # First try standard JWT header authentication
            return super().authenticate(request)
        except Exception as e:
            # If header authentication fails, try session authentication
            return None