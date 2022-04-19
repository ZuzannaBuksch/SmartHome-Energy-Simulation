from django.contrib import admin

from .models import (Building, Device, DeviceRaport, EnergyGenerator,
                     EnergyReceiver, EnergyStorage, Room)

admin.site.register(DeviceRaport)
admin.site.register(Device)
admin.site.register(Building)
admin.site.register(EnergyStorage)
admin.site.register(EnergyReceiver)
admin.site.register(EnergyGenerator)
admin.site.register(Room)

# Register your models here.
