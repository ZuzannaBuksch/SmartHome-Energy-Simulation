from rest_framework import serializers
from rest_polymorphic.serializers import PolymorphicSerializer

from .models import (Building, Device, DeviceRaport, EnergyGenerator,
                     EnergyReceiver, EnergyStorage, Room)


class EnergyGeneratorSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    class Meta:
        model = EnergyGenerator
        fields = ('id', 'building', 'name', 'state', 'room','efficiency', 'type', 'generation_power')


class EnergyReceiverSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    class Meta:
        model = EnergyReceiver
        fields = ('id', 'building', 'name', 'state', 'room', 'device_power', 'type', 'supply_voltage')


class EnergyStorageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    class Meta:
        model = EnergyStorage
        fields = ('id', 'building', 'name', 'state', 'room', 'capacity', 'battery_charge', 'type', 'battery_voltage')


class DeviceSerializer(PolymorphicSerializer):
    model_serializer_mapping = {
            EnergyGenerator: EnergyGeneratorSerializer,
            EnergyReceiver: EnergyReceiverSerializer,
            EnergyStorage: EnergyStorageSerializer
        }

class RoomSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    room_devices = DeviceSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = "__all__"
        extra_fields = ["room_devices"]


class BuildingSerializer(serializers.ModelSerializer):
    # user = serializers.HiddenField(
    #     default=serializers.CreateOnlyDefault(serializers.CurrentUserDefault())
    # )
    id = serializers.IntegerField()
    building_rooms = RoomSerializer(many=True, read_only=True)
    building_devices = DeviceSerializer(many=True, read_only=True)

    class Meta:
        model = Building
        fields = "__all__"
        extra_fields = ["building_rooms", "building_devices"]


class BuildingListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    class Meta:
        model = Building
        fields = "__all__"


class DeviceRaportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceRaport
        fields = "__all__"


class DeviceRaportListSerializer(serializers.Serializer):
    raports = serializers.ListField(child=DeviceRaportSerializer())


class PopulateDatabaseSerializer(serializers.Serializer):
    data = serializers.CharField()


class BuildingEnergySerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", input_formats=['%Y-%m-%d %H:%M:%S'])
    end_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", input_formats=['%Y-%m-%d %H:%M:%S'], required=False)


