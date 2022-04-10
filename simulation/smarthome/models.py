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
    state = models.BooleanField(null=False, default=False)
    room = models.ForeignKey(
        Room, related_name="room_devices", null=False, on_delete=models.CASCADE
    )

    @property
    def type(self):
        return self.__class__.__name__


class EnergyReceiver(Device):
    energy_consumption = models.FloatField()

    def __str__(self):
        return f"Energy receiving device: {str(self.id)} | name: {self.name}"


class EnergyGenerator(Device):
    energy_generation = models.FloatField()
    efficiency = models.FloatField()
    
    def __str__(self):
        return f"Energy generating device: {str(self.id)} | name: {self.name}"


class EnergyStorage(Device):
    capacity = models.FloatField()
    battery_charge = models.FloatField()
    
    def __str__(self):
        return f"Energy storing device: {str(self.id)} | name: {self.name}"


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

# class WeatherRaport(models.Model):
#     datetime_from = models.DateTimeField()
#     datetime_to = models.DateTimeField(null=True, blank=True)

#     class Meta:
#         unique_together = ('datetime_from', 'datetime_to',)


#     def __str__(self):
#         return f"Weather raport: {str(self.id)}"
