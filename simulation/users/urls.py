from django.urls import include, path
from .views import UserViewSet, UserBuildingsView
from rest_framework import routers

app_name = "users"


router = routers.SimpleRouter()
router.register(r"users", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    path("users/<int:pk>/buildings/", UserBuildingsView.as_view(), name="user-buildings"),
]
