from django.urls import include, path
from rest_framework import routers

from .views import (
    BuildingViewSet,
    DeviceViewSet,
    RoomViewSet,
    PopulateDatabaseView,
    BuildingEnergyView,
    # BuildingDevicesView,
)

app_name = "smarthome"


router = routers.SimpleRouter()
router.register(r"devices", DeviceViewSet)
router.register(r"buildings", BuildingViewSet)
router.register(r"rooms", RoomViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "populate/", 
        PopulateDatabaseView.as_view(), 
        name="populate"
        ),
    path(
        "buildings/<int:pk>/energy/",
        BuildingEnergyView.as_view(),
        name="energy"
    ),
    # path("buildings/<int:pk>/devices/", BuildingDevicesView.as_view(), name="building-devices"),
]
