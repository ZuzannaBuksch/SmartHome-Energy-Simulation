from datetime import datetime

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
    capacity = models.FloatField() #[Ah]
    battery_voltage = models.FloatField(null=True, blank=True) # You are trying to add a non-nullable field 'battery_voltage' to energystorage without a default; we can't do that (t (the database needs something to populate existing rows).
    
    def __str__(self):
        return f"Energy storing device: {str(self.id)} | name: {self.name}"

    def save(self, *args, **kwargs):
        super(EnergyStorage, self).save(*args, **kwargs)
        ChargeStateRaport.objects.create(device = self, charge_value = 0.0, date = datetime.now())

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
        
class StorageChargingAndUsageRaport(models.Model):
    CHARGING = 'CHARGING'
    USAGE = 'USAGE'
    job_types = [
        (CHARGING, "charging"),
        (USAGE, "usage"),
    ]
    job_type = models.CharField(max_length=8, choices=job_types)
    date_time_from = models.DateTimeField()
    date_time_to = models.DateTimeField(null=True, blank=True)
    device = models.ForeignKey(
        EnergyStorage, on_delete=models.CASCADE, related_name="storage_charging_and_usage_raports"
    )
    energy_receiver = models.ForeignKey(
        EnergyReceiver, null=True, blank=True, on_delete=models.CASCADE, related_name="storage_usage_devices_raports_v2"
    )

    class Meta:
        unique_together = ('device', 'date_time_from',)


    def __str__(self):
        return f"Storage charging and usage raport: {str(self.id)} | device: {self.device.name}"

class ChargeStateRaport(models.Model):
    date = models.DateTimeField()
    device = models.ForeignKey(
        EnergyStorage, null=True, on_delete=models.CASCADE, related_name="charge_state_raports"
    )
    charge_value = models.FloatField() 
    class Meta:
        unique_together = ('device', 'date',)


    def __str__(self):
        return f"Charge state raport: {str(self.id)} | device: {self.device.name}"
