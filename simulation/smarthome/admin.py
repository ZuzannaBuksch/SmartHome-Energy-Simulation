from django.contrib import admin
from .models import Device, Building, DeviceRaport, EnergyGenerator, EnergyReceiver, EnergyStorage

admin.site.register(DeviceRaport)
admin.site.register(Device)
admin.site.register(Building)
admin.site.register(EnergyStorage)
admin.site.register(EnergyReceiver)
admin.site.register(EnergyGenerator)

# Register your models here.
