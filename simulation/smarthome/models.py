from datetime import datetime
from xml.dom import ValidationErr

from django.db import models
from polymorphic.models import PolymorphicModel
from users.models import User


class Building(models.Model):
    name = models.CharField(max_length=100, null=True)
    icon = models.IntegerField(null=True, blank=True, default=0)
    user = models.ForeignKey(
        User, related_name="user_buildings", null=False, on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Building: {str(self.id)} | name: {self.name}"

class Room(models.Model):
    name = models.CharField(max_length=100, null=True)
    area = models.DecimalField(max_digits=4, decimal_places=1, null=False, blank=False)
    building = models.ForeignKey(
        Building, related_name="building_rooms", null=False, on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Room: {str(self.id)} | name: {self.name}"

class Device(PolymorphicModel):
    name = models.CharField(max_length=100, null=False)
    state = models.BooleanField(null=True, default=False)
    room = models.ForeignKey(
        Room, related_name="room_devices", null=True, blank=True, on_delete=models.SET_NULL
    )
    building = models.ForeignKey(
        Building, related_name="building_devices", on_delete=models.CASCADE
    )

    @property
    def type(self):
        return self.__class__.__name__


class EnergyReceiver(Device):
    device_power = models.FloatField() 
    supply_voltage = models.FloatField() 

    def __str__(self):
        return f"Energy receiving device: {str(self.id)} | name: {self.name}"


class EnergyGenerator(Device):
    generation_power = models.FloatField()
    
    def __str__(self):
        return f"Energy generating device: {str(self.id)} | name: {self.name}"


class EnergyStorage(Device):
    capacity = models.FloatField()
    battery_charge = models.FloatField(null=True, blank=True) # You are trying to add a non-nullable field 'battery_voltage' to energystorage without a default; we can't do that (t (the database needs something to populate existing rows).
    battery_voltage = models.FloatField(null=True, blank=True) # You are trying to add a non-nullable field 'battery_voltage' to energystorage without a default; we can't do that (t (the database needs something to populate existing rows).
    
    def __str__(self):
        return f"Energy storing device: {str(self.id)} | name: {self.name}"

class DevicePowerSupplyRaport(models.Model):
    connected_from= models.DateTimeField()
    connected_to = models.DateTimeField(null=True, blank=True)
    device = models.ForeignKey(
        Device, null=True, on_delete=models.CASCADE, related_name="device_power_raports"
    )
    energy_receiver = models.ForeignKey(
        EnergyReceiver, null=True, on_delete=models.CASCADE, related_name="receiver_power_raports"
    )

class DeviceRaport(models.Model):
    turned_on = models.DateTimeField()
    turned_off = models.DateTimeField(null=True, blank=True)
    device = models.ForeignKey(
        Device, null=True, on_delete=models.CASCADE, related_name="device_raports"
    )

    class Meta:
        unique_together = ('device', 'turned_on',)


    def __str__(self):
        return f"Device raport: {str(self.id)} | device: {self.device.name}"

class WeatherRaport(models.Model):
    datetime_from = models.DateTimeField()
    datetime_to = models.DateTimeField(null=True, blank=True)
    solar_radiation = models.FloatField()
    temperature = models.FloatField()
    wind_speed = models.FloatField()

    def __str__(self):
        return f"Weather raport: {str(self.id)}"
