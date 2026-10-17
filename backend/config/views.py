from rest_framework.views import APIView 
from rest_framework.decorators import api_view, authentication_classes
from rest_framework import status
from rest_framework.response import Response
import jwt
from .authentication import JWTAuthentication
from django.conf import settings
from datetime import datetime, timedelta
from .tenant_registry import global_user_map
from .tenant_context import tenant_db_context, get_current_tenant_db


class LoginView(APIView):
    def post(self, request):
        identifier = request.data.get("identifier")
        password = request.data.get("password")
        user_map = global_user_map.get(identifier)
        if not user_map:
            return Response({"message": "user not found"},status= status.HTTP_401_UNAUTHORIZED)
        stored_password= user_map.get("password")
        if password == stored_password:
            payload={
                "sub": identifier,
                "emp_id": user_map["emp_id"],
                "role": user_map["role"],
                "tenant_db": user_map["tenant_db"],
                "exp": datetime.utcnow()+ timedelta(hours=1)
            }

            token= jwt.encode(payload,settings.SECRET_KEY, algorithm = "HS256")
            return Response({"token":token})
        else:
            return Response({"message":"invalid password"},status = 404)



@api_view(['GET'])
@authentication_classes([JWTAuthentication])
def employee(request):
    with tenant_db_context(request.auth["tenant_db"]):
        current_tenant= get_current_tenant_db()
        response_data = {
            "tenant_db":current_tenant,
        }
    print("After request block:", get_current_tenant_db())
    return Response(response_data)

    