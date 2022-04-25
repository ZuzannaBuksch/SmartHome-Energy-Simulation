from rest_framework import serializers

from .models import (Building, Device, DeviceRaport, EnergyGenerator,
                     EnergyReceiver, EnergyStorage, Room)


class EnergyGeneratorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyGenerator
        fields = ('id', 'name', 'state', 'room','efficiency', 'type', 'generation_power')
        read_only_fields = ('id', 'type',)


class EnergyReceiverSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyReceiver
        fields = ('id', 'name', 'state', 'room', 'device_power', 'type', 'supply_voltage')
        read_only_fields = ('id', 'type',)


class EnergyStorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyStorage
        fields = ('id', 'name', 'state', 'room', 'capacity', 'battery_charge', 'type', 'battery_voltage')
        read_only_fields = ('id', 'type',)


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ('id', 'name', 'state', 'room', 'type')
        read_only_fields = ('id', 'type',)

    def to_internal_value(self, data):
        """
        Because Device is Polymorphic
        """
        if data.get('type') == "EnergyGenerator":
            self.Meta.model = EnergyGenerator
            return EnergyGeneratorSerializer(context=self.context).to_internal_value(data)
        elif data.get('type') == "EnergyReceiver":
            self.Meta.model = EnergyReceiver
            return EnergyReceiverSerializer(context=self.context).to_internal_value(data)
        elif data.get('type') == "EnergyStorage":
            self.Meta.model = EnergyStorage
            return EnergyStorageSerializer(context=self.context).to_internal_value(data)

        self.Meta.model = Device
        return super(DeviceSerializer, self).to_internal_value(data)

class RoomSerializer(serializers.ModelSerializer):
    room_devices = DeviceSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = "__all__"
        extra_fields = ["room_devices"]


class BuildingSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CreateOnlyDefault(serializers.CurrentUserDefault())
    )
    building_rooms = RoomSerializer(many=True, read_only=True)
    building_devices = DeviceSerializer(many=True, read_only=True)

    class Meta:
        model = Building
        fields = "__all__"
        extra_fields = ["building_rooms", "building_devices"]


class BuildingListSerializer(serializers.ModelSerializer):
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



