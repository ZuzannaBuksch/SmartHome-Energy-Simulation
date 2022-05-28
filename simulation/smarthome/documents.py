from config.settings import ELASTICSEARCH_CONNECTION
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from elasticsearch_dsl import connections

from .models import (ChargeStateRaport, Device, DeviceRaport,
                     StorageChargingAndUsageRaport, WeatherRaport)

connections.create_connection(**ELASTICSEARCH_CONNECTION)

@registry.register_document
class DeviceRaportDocument(Document):
    id = fields.IntegerField(attr='id')
    device = fields.ObjectField(properties={
            'name' : fields.TextField(),
            'id' : fields.IntegerField(attr='id'),
    })

    class Index:
        name = 'device_raports'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    
    class Django:
        model = DeviceRaport
        fields = [
            'turned_on',
            'turned_off',
        ]
    
    def get_queryset(self):
        return super(DeviceRaportDocument, self).get_queryset().select_related(
            'device'
        )

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Device):
            return related_instance.device_raports.all()



@registry.register_document
class WeatherDocument(Document):
    class Index:
        name = 'weather_raports'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    
    class Django:
        model = WeatherRaport
        fields = [
            'datetime_from',
            'datetime_to',
            'solar_radiation', 
            'temperature', 
            'wind_speed',
        ]

@registry.register_document
class StorageChargingAndUsageDocument(Document):
    id = fields.IntegerField(attr='id')
    device = fields.ObjectField(properties={
            'name' : fields.TextField(),
            'id' : fields.IntegerField(attr='id')
    })

    energy_receiver = fields.ObjectField(properties={
            'name' : fields.TextField(),
            'id' : fields.IntegerField(attr='id'),
            'device_power' : fields.FloatField()
            
    })

    class Index:
        name = 'storage_charging_and_usage_raports'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    
    class Django:
        model = StorageChargingAndUsageRaport
        fields = [
            'date_time_from',
            'date_time_to',
            'job_type',
        ]
    
    def get_queryset(self):
        return super(StorageChargingAndUsageDocument, self).get_queryset().select_related(
            'device'
        )

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Device):
            return related_instance.storage_charging_and_usage_raports.all()

@registry.register_document
class ChargeStateDocument(Document):
    id = fields.IntegerField(attr='id')
    device = fields.ObjectField(properties={
            'name' : fields.TextField(),
            'id' : fields.IntegerField(attr='id'),
    })

    class Index:
        name = 'charge_state_raports'
        settings = {'number_of_shards': 1,
                    'number_of_replicas': 0}
    
    class Django:
        model = ChargeStateRaport
        fields = [
            'date',
            'charge_value',
        ]
    

    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Device):
            return related_instance.charge_state_raports.all()

# @registry.register_document
# class DevicePowerSupplyDocument(Document):
#     device = fields.ObjectField(properties={
#             'name' : fields.TextField(),
#             'id' : fields.IntegerField(attr='id'),
#     })

#     energy_receiver = fields.ObjectField(properties={
#             'name' : fields.TextField(),
#             'id' : fields.IntegerField(attr='id'),
#     })

#     class Index:
#         name = 'device_power_supply_raports'
#         settings = {'number_of_shards': 1,
#                     'number_of_replicas': 0}
    
#     class Django:
#         model = DevicePowerSupplyRaport
#         fields = [
#             'connected_from',
#             'connected_to',
#         ]
    
#     def get_queryset(self):
#         return super(DevicePowerSupplyDocument, self).get_queryset().select_related(
#             'device'
#         )

#     def get_instances_from_related(self, related_instance):
#         if isinstance(related_instance, Device):
#             return related_instance.device_power_raports.all()
