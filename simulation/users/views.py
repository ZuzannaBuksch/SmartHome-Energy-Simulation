

from rest_framework.response import Response
from smarthome.models import Building
from smarthome.serializers import BuildingListSerializer
from users.models import User
from .serializers import UserRegistrationSerializer
from rest_framework import viewsets, generics, status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [
        AllowAny,
    ]


class UserBuildingsView(generics.ListAPIView):
    queryset = Building.objects.all()
    serializer_class = BuildingListSerializer
    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        return self.queryset.filter(user__pk=self.kwargs["pk"])

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, id=kwargs.get("pk"))
        buildings_data = request.data
        for building in request.data:
            building["user"] = user.id

        serializer = self.serializer_class(data=buildings_data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
