import json
from datetime import datetime

from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.models import User

from .models import (Building, Device, DeviceRaport, EnergyGenerator,
                     EnergyReceiver, EnergyStorage, Room)
from .models_calculators import DeviceCalculateManager
from .serializers import (BuildingListSerializer, BuildingSerializer,
                          DeviceRaportListSerializer, DeviceSerializer,
                          PopulateDatabaseSerializer, RoomSerializer)


class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.all()
    serializer_class = BuildingSerializer
    list_serializer_class = BuildingListSerializer
    permission_classes = [
        AllowAny,
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return self.list_serializer_class
        return self.serializer_class

    # def get_queryset(self):
    #     return self.request.user.user_buildings.all()


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [
        AllowAny,
    ]

    def partial_update(self, request, *args, **kwargs):
        device = self.get_object()
        cached_state = device.state
        json_device = super().partial_update(request, *args, **kwargs)
        if json_device.data.get('state') != cached_state:
            if json_device.data.get('state') == True:
                device_raport = DeviceRaport(device=device, turned_on=datetime.now())
                device_raport.save()
            elif json_device.data.get('state') == False:
                device_raport = DeviceRaport.objects.filter(device=device).last()
                device_raport.turned_off = datetime.now()
                device_raport.save()
        return json_device
        

class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [
        AllowAny,
    ]


class PopulateDatabaseView(mixins.CreateModelMixin, generics.GenericAPIView):
    serializer_class = PopulateDatabaseSerializer
    permission_classes = [
        AllowAny,
    ]
    device_classes = {
            "EnergyReceiver": EnergyReceiver,
            "EnergyGenerator": EnergyGenerator,
            "EnergyStorage": EnergyStorage
    }


    @classmethod
    def get_extra_actions(cls):
        return []

    def post(self, request, *args, **kwargs):
        generated_raports = []
        request_data = json.loads(request.data.get('data'))
        for user_data in request_data:
            user = User.objects.get_or_create(email=user_data.get("email"))[0]
            user.save()
            for building_data in user_data.get("buildings"):
                building = Building.objects.get_or_create(user=user, name=building_data.get("name"))[0]
                building.save()
                for room_data in building_data.get("building_rooms"):
                    room = Room.objects.get_or_create(building=building, name=room_data.get("name"), area=room_data.get("area"))[0]
                    room.save()
                    for device_data in room_data.get("room_devices"):
                        dev_class = self.device_classes.get(device_data.pop("type"))
                        raports = device_data.pop("device_raports")
                        device = dev_class.objects.get_or_create(room=room, **device_data)[0]
                        device.save()
                        for raport_data in raports:
                            generated_raports.append(DeviceRaport(device=device, **raport_data))
        devices = DeviceRaport.objects.bulk_create(generated_raports, ignore_conflicts=True)
        serializer = DeviceRaportListSerializer(instance={"raports":devices})
        return Response({"data": serializer.data})

class BuildingEnergyView(mixins.RetrieveModelMixin, generics.GenericAPIView):
    permission_classes = [
        AllowAny,
    ]

    @classmethod
    def get_extra_actions(cls):
        return []
    
    # api/smarthome/energy/1?start_date=30-03-2022 10:02:01
    def get(self, request, *args, **kwargs):
        building = get_object_or_404(Building, pk=kwargs.get('pk'))
        building_dict = model_to_dict(building)
        building_dict["building_devices"] = []
        for device in building.building_devices.all():
            start_date = request.query_params.get("start_date")
            building_dict["building_devices"].append(DeviceCalculateManager().get_device_energy(device, start_date))
        return Response(building_dict)
