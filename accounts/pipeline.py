from rest_framework_simplejwt.tokens import RefreshToken

def generate_jwt(backend, user, response, *args, **kwargs):
    refresh = RefreshToken.for_user(user)
    response['jwt_access'] = str(refresh.access_token)
    response['jwt_refresh'] = str(refresh)
    return response
