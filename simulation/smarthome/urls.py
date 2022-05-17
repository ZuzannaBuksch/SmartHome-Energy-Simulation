from django.urls import include, path
from rest_framework import routers

from .views import (
    BuildingViewSet,
    DeviceViewSet,
    RoomViewSet,
    PopulateDatabaseView,
    BuildingEnergyView,
    BuildingDevicesView,
    RaportsFromJsonFileViewSet,
    DeviceRaportsView,
)

app_name = "smarthome"


router = routers.SimpleRouter()
router.register(r"devices", DeviceViewSet)
router.register(r"buildings", BuildingViewSet)
router.register(r"rooms", RoomViewSet)
router.register(r"json-raports", RaportsFromJsonFileViewSet)

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
    path("buildings/<int:pk>/devices/", BuildingDevicesView.as_view(), name="building-devices"),
    path("devices/<int:pk>/device-raports/", DeviceRaportsView.as_view(), name="device-raports"),
]
