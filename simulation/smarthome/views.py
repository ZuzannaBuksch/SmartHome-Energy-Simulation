import json
from datetime import datetime

from django.db import transaction
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (Building, ChargeStateRaport, Device, DeviceRaport,
                     EnergyStorage, StorageChargingAndUsageRaport)
from .models_calculators import DeviceCalculateManager, EnergyCalculator
from .serializers import (BuildingListSerializer, BuildingSerializer,
                          ChargeStateRaportSerializer, DatesRangeSerializer,
                          DeviceRaportSerializer, DeviceSerializer,
                          StorageChargingAndUsageRaportSerializer)


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

    def retrieve(self, request, *args, **kwagrs):
        response = super().retrieve(request, *args, **kwagrs)
        device = self.get_object()
        if device.type == EnergyStorage.__name__:
            serializer = DatesRangeSerializer(data=request.query_params)
            if serializer.is_valid(raise_exception=True):
                start_date = serializer.to_internal_value(serializer.data).get("start_date")
                end_date = serializer.to_internal_value(serializer.data).get("end_date")
                raports_docs = EnergyCalculator.filter_storage_raports_by_device_and_date(device, start_date, end_date)
                raports = [StorageChargingAndUsageRaport.objects.get(id=raport.id) for raport in raports_docs]
                response.data["raports"] = [model_to_dict(raport) for raport in raports]
        return Response(data=response.data, status=response.status_code)

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
        serializer = DatesRangeSerializer(data=request.query_params)
        if serializer.is_valid():
            start_date = serializer.to_internal_value(serializer.data).get("start_date")
            end_date = serializer.to_internal_value(serializer.data).get("end_date")
            building_dict["building_devices"] = []
            for device in building.building_devices.all():
                if device.type == EnergyStorage.__name__:
                    continue
                building_dict["building_devices"].append(DeviceCalculateManager().get_device_energy(device, start_date, end_date))
            return Response(building_dict)
        else:
           return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BuildingStorageEnergyView(mixins.RetrieveModelMixin, generics.GenericAPIView):
    permission_classes = [
        AllowAny,
    ]
    queryset = Building.objects.all()

    @classmethod
    def get_extra_actions(cls):
        return []
    
    # api/buildings/1/energy-storage?start_date=30-03-2022 10:02:01
    def get(self, request, *args, **kwargs):
        building = self.get_object()
        building_dict = model_to_dict(building)
        serializer = DatesRangeSerializer(data=request.query_params)
        if serializer.is_valid():
            start_date = serializer.to_internal_value(serializer.data).get("start_date")
            end_date = serializer.to_internal_value(serializer.data).get("end_date")
            building_dict["building_devices"] = []
            for device in building.building_devices.all():
                if device.type != EnergyStorage.__name__:
                    continue
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
            if serializer.is_valid(raise_exception=True):
                serializer.save()
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=serializer.data, status=status.HTTP_200_OK)
        
class DeviceRaportsView(generics.ListAPIView):
    queryset = DeviceRaport.objects.all()
    serializer_class = DeviceRaportSerializer
    storage_serializer_class = StorageChargingAndUsageRaportSerializer
    permission_classes = [
        AllowAny,
    ]

    def get_serializer_class(self, *args, **kwargs):
        if kwargs.get("device_type") == EnergyStorage.__name__:
            return self.storage_serializer_class
        return self.serializer_class


    @transaction.atomic
    def post(self, request, *args, **kwargs):
        device = get_object_or_404(Device, id=kwargs.get("pk"))
        raports_data = request.data
        for raport in raports_data:  #must be in a loop because polymorphic not allow to serialize many
            raport["device"] = device.id
            serializer = self.get_serializer_class(device_type=device.type)(data=raport)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                pass
            else:
                return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        device = get_object_or_404(Device, id=kwargs.get("pk"))
        date_serializer = DatesRangeSerializer(data=request.query_params)
        if date_serializer.is_valid(raise_exception=True):
            start_date = date_serializer.to_internal_value(date_serializer.data).get("start_date")
            end_date = date_serializer.to_internal_value(date_serializer.data).get("end_date")
        else:
            return Response(serializer.errors)

        if device.type == EnergyStorage.__name__: 
            raports_docs = EnergyCalculator.filter_storage_raports_by_device_and_date(device, start_date, end_date)
            raports = [StorageChargingAndUsageRaport.objects.get(id=raport.id) for raport in raports_docs]
            serializer = StorageChargingAndUsageRaportSerializer(raports, many=True)
        else:
            raports_docs = EnergyCalculator.filter_raports_by_device_and_date(device, start_date, end_date)
            raports = [DeviceRaport.objects.get(id=raport.id) for raport in raports_docs]
            serializer = DeviceRaportSerializer(raports, many=True)
        return Response(serializer.data)

class ChargeStateRaportView(generics.ListCreateAPIView):
    queryset = ChargeStateRaport.objects.all()
    serializer_class = ChargeStateRaportSerializer
    permission_classes = [
        AllowAny,
    ]

    def get_queryset(self):
        queryset = self.queryset
        device_queryset = [queryset.filter(device__pk=self.kwargs["pk"]).latest("date")]
        return device_queryset
    
    # @transaction.atomic
    # def post(self, request, *args, **kwargs):
    #     device = get_object_or_404(EnergyStorage, id=kwargs.get("pk"))
    #     raports_data = request.data
    #     for raport in raports_data:  #must be in a loop because polymorphic not allow to serialize many
    #         raport["device"] = device.id
    #         serializer = self.serializer_class(data=raport)
    #         if serializer.is_valid(raise_exception=True):
    #             serializer.save()
    #         else:
    #             return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    #     return Response(data=serializer.data, status=status.HTTP_200_OK)
