import json
from datetime import datetime

from django.forms.models import model_to_dict
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.models import User

from .models import (Building, Device, DeviceRaport, EnergyGenerator,
                     EnergyReceiver, EnergyStorage, Room)
from .models_calculators import DeviceCalculateManager
from .serializers import (BuildingListSerializer, BuildingSerializer, 
                          DeviceRaportListSerializer, DeviceRaportSerializer, DeviceSerializer,
                          PopulateDatabaseSerializer, RoomSerializer, BuildingEnergySerializer)
from django.shortcuts import get_object_or_404
from django.db import transaction


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
                for device_data in building_data.get("building_devices"):
                    dev_class = self.device_classes.get(device_data.pop("type"))
                    raports = device_data.pop("device_raports")
                    device = dev_class.objects.get_or_create(building=building, **device_data)[0]
                    device.save()
                    for raport_data in raports:
                        generated_raports.append(DeviceRaport(device=device, **raport_data))
        devices = DeviceRaport.objects.bulk_create(generated_raports, ignore_conflicts=True)
        serializer = DeviceRaportListSerializer(instance={"raports":devices})
        return Response({"data": serializer.data})


class RaportsFromJsonFileViewSet(viewsets.ModelViewSet):
    queryset = DeviceRaport.objects.all()
    serializer_class = DeviceRaportSerializer
    permission_classes = [
        AllowAny,
    ]

    @transaction.atomic
    def create(self, request):
        with open("raports.txt", "r") as f:
            devices = json.load(f)
        generated_raports = []
        for device_data in devices:
            device_id = device_data.get("device")
            device = Device.objects.get(id=device_id)
            for raport_data in device_data.get("raports"):
                if not raport_data.get("turned_off"):
                    raport_data.pop("turned_off")
                generated_raports.append(DeviceRaport(device=device, **raport_data))
        devices = DeviceRaport.objects.bulk_create(generated_raports, ignore_conflicts=True)
        serializer = DeviceRaportListSerializer(instance={"raports":devices})
        return Response({"data": serializer.data})


class BuildingEnergyView(mixins.RetrieveModelMixin, generics.GenericAPIView):
    permission_classes = [
        AllowAny,
    ]
    queryset = Building.objects.all()

    @classmethod
    def get_extra_actions(cls):
        return []
    
    # api/buildings/1/energy?start_date=30-03-2022 10:02:01
    def get(self, request, *args, **kwargs):
        building = self.get_object()
        building_dict = model_to_dict(building)
        serializer = BuildingEnergySerializer(data=request.query_params)
        if serializer.is_valid():
            start_date = serializer.to_internal_value(serializer.data).get("start_date")
            end_date = serializer.to_internal_value(serializer.data).get("end_date")
            print(start_date, end_date)
            building_dict["building_devices"] = []
            for device in building.building_devices.all():
                building_dict["building_devices"].append(DeviceCalculateManager().get_device_energy(device, start_date, end_date))
            return Response(building_dict)
        else:
           return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BuildingDevicesView(generics.ListAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        return self.queryset.filter(building__pk=self.kwargs["pk"])

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        building = get_object_or_404(Building, id=kwargs.get("pk"))
        device_data = request.data
        for device in device_data:  #must be in a loop because polymorphic not allow to serialize many
            device["building"] = building.id
            device["resourcetype"] = device.get("type")
            serializer = self.serializer_class(data=device)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=serializer.data, status=status.HTTP_200_OK)
        
class DeviceRaportsView(generics.ListAPIView):
    queryset = DeviceRaport.objects.all()
    serializer_class = DeviceRaportSerializer
    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        return self.queryset.filter(device__pk=self.kwargs["pk"])

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        device = get_object_or_404(Device, id=kwargs.get("pk"))
        raports_data = request.data
        for raport in raports_data:  #must be in a loop because polymorphic not allow to serialize many
            raport["device"] = device.id
            serializer = self.serializer_class(data=raport)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                pass
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=serializer.data, status=status.HTTP_200_OK)
        
