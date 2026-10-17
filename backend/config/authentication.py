from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
import jwt
from django.conf import settings
from .tenant_registry import global_user_map

class JWTAuthentication(BaseAuthentication):
    def authenticate(self,request):
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise AuthenticationFailed("Token required")
        if not authorization.startswith("Bearer "):
            raise AuthenticationFailed("Invalid Authentication Header")

        token= authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = payload["emp_id"]
            tenant_db = payload["tenant_db"]
            return user,payload

        except jwt.InvalidTokenError:
            raise AuthenticationFailed("invalid token")
