from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    SessionAuthentication scheme that doesn't enforce CSRF.
    """
    def enforce_csrf(self, request):
        return  # Skip CSRF check 