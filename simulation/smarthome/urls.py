from django.urls import include, path
from rest_framework import routers

from .views import (
    BuildingViewSet,
    DeviceViewSet,
    BuildingEnergyView,
    BuildingDevicesView,
    DeviceRaportsView,
    BuildingStorageEnergyView,
    ChargeStateRaportView,
)

app_name = "smarthome"


router = routers.SimpleRouter()
router.register(r"devices", DeviceViewSet)
router.register(r"buildings", BuildingViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "buildings/<int:pk>/energy/",
        BuildingEnergyView.as_view(),
        name="energy"
    ),
    path(
        "buildings/<int:pk>/energy-storage/",
        BuildingStorageEnergyView.as_view(),
        name="storage_energy"
    ),
    path("buildings/<int:pk>/devices/", BuildingDevicesView.as_view(), name="building-devices"),
    path("devices/<int:pk>/device-raports/", DeviceRaportsView.as_view(), name="device-raports"),
    path("devices/<int:pk>/charge-state-raports/", ChargeStateRaportView.as_view(), name="charge-state-raports"),
]
