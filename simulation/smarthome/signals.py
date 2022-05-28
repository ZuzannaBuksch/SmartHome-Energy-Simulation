# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from django_elasticsearch_dsl.registries import registry


@receiver(post_save)
def update_document(sender, **kwargs):
    app_label = sender._meta.app_label
    model_name = sender._meta.model_name
    instance = kwargs['instance']

    if app_label == 'device_raports':
        if model_name == 'DeviceRaport':
            instances = instance.device_raport.all()
            for _instance in instances:
                registry.update(_instance)

    if app_label == 'weather_raports':
        if model_name == 'WeatherRaport':
            instances = instance.weather_raport.all()
            for _instance in instances:
                registry.update(_instance)

    if app_label == 'storage_charging_and_usage_raports':
        if model_name == 'StorageChargingAndUsageRaport':
            instances = instance.storage_charging_and_usage_raport.all()
            for _instance in instances:
                registry.update(_instance)

    if app_label == 'charge_state_raports':
        if model_name == 'ChargeStateRaport':
            instances = instance.charge_state_raport.all()
            for _instance in instances:
                registry.update(_instance)

@receiver(post_delete)
def delete_document(sender, **kwargs):
    app_label = sender._meta.app_label
    model_name = sender._meta.model_name
    instance = kwargs['instance']

    if app_label == 'device_raports':
        if model_name == 'DeviceRaport':
            instances = instance.device_raport.all()
            for _instance in instances:
                registry.update(_instance)

    if app_label == 'weather_raports':
        if model_name == 'WeatherRaport':
            instances = instance.weather_raport.all()
            for _instance in instances:
                registry.update(_instance)

    if app_label == 'storage_charging_and_usage_raports':
        if model_name == 'StorageChargingAndUsageRaport':
            instances = instance.storage_charging_and_usage_raport.all()
            for _instance in instances:
                registry.update(_instance)

    if app_label == 'charge_state_raports':
        if model_name == 'ChargeStateRaport':
            instances = instance.charge_state_raport.all()
            for _instance in instances:
                registry.update(_instance)
