from abc import ABC
from datetime import datetime, timedelta
import re
from typing import Dict
from xmlrpc.client import DateTime

from django.forms.models import model_to_dict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from .weather import Weather

from .documents import DeviceRaportDocument, WeatherDocument
from .models import Device, DeviceRaport, EnergyGenerator, EnergyReceiver

client = Elasticsearch()

class DeviceCalculateManager():
    """Manager class for choosing strategy for calculating device energy data"""

    def get_device_energy(self, device: Device, start_date: datetime=None) -> dict:
        device_type = {
            "EnergyReceiver": EnergyReceiverCalculator,
            "EnergyGenerator": EnergyGeneratorCalculator,
            "EnergyStorage": EnergyStorageCalculator,
        }.get(device.type)
        try:
            if(device.type == EnergyReceiver):
                return device_type().get_receiver_energy_calculation(device, start_date)
            if(device.type == EnergyGenerator):
                return device_type().get_generator_energy_calculation(device, start_date)
        except AttributeError:
            return {}

class EnergyCalculator(ABC):
    """Abstract class that provides interface with methods for concrete energy calculators"""

    def get_receiver_energy_calculation(self, device: Device, start_date: datetime=None) -> dict:
        device_raports = self._filter_raports_by_device_and_date(device, start_date)
        return {
            **model_to_dict(device),
            **self._calculate_energy_data(device, device_raports),
        }

    def get_generator_energy_calculation(self, device: Device, start_date: datetime=None) -> dict:
        weather_raports = self._filter_weather_raports_by_date(start_date)
        return {
            **model_to_dict(device),
            **self._calculate_energy_data(device, weather_raports),
        }

    def _filter_raports_by_device_and_date(self, device: Device, start_date: datetime=None) -> Search:
        raports = DeviceRaportDocument.search().query('match', device__id=device.id)
        if start_date:
            raports = raports.filter("range", turned_on={"gte": start_date})
        return raports
    
    def _filter_weather_raports_by_date(self, start_date: datetime=None) -> Search:
        raports = WeatherDocument
        if start_date:
            raports = WeatherDocument.filter("range", turned_on={"gte": start_date})
        return raports

    def _calculate_difference_in_time(self, turned_on: datetime, turned_off: datetime) -> float:
        diff = turned_off - turned_on
        diff_in_hours = diff.total_seconds() / 3600
        return diff_in_hours
        

class EnergyReceiverCalculator(EnergyCalculator):
    """Energy calculating class for energy receiving devices"""

    def _calculate_energy_data(self, device: Device, device_raports: Search) -> Dict[str, float]:
        """Calculate energy consumptioned by the device in a given time.

        Arguments:
        device -- instance of a device for calculating energy consumption for
        device_raports -- device power raports filtered by elasticsearch 
        """
        sum_of_hours = 0.0
        for raport in device_raports:
            if raport.turned_off is None:
                turned_off = datetime.now
            else:
                turned_off = raport.turned_off
            diff_in_hours = self._calculate_difference_in_time(raport.turned_on, turned_off)
            sum_of_hours += diff_in_hours

        kwh_factor = device.energy_consumption / 1000 * sum_of_hours #think about rounding this factor 
        return {"energy_consumed": kwh_factor}

class EnergyGeneratorCalculator(EnergyCalculator):
    """Energy calculating class for energy generating devices"""

    #-------------------------calculations only for PV's----------------------------------
    #     # raports = WeatherDocument.filter("range", turned_on={"gte": start_date}) what if there will be a start date in reports, e.g.:
    # ... 16:05:00, 16:04:30, 16:05:30 ... and we are interested in e.g. "start_date" = 16:04.51 btw. troche nie rozumiem tego filtrowania - spytać Pauliny jak to działa, parametry range etc.

    min_solar_radiation = 0 #W/m^2
    max_solar_radiation = 1000 #W/m^2
    weather_loss_factor = 0.05

    def _get_weather_coefficient(self, solar_radiation: float, min_range: int, max_range: int):
        weight = ((solar_radiation - self.min_solar_radiation) / (self.max_solar_radiation - self.min_solar_radiation)) * (max_range - min_range) + min_range
        return weight
    
    def _calculate_power_of_photovoltaic(self, solar_radiation_coefficient: float, generator_power: float):
        output_power = generator_power * solar_radiation_coefficient * self.weather_loss_factor
        if output_power > generator_power or output_power < 0.0:
            raise ValueError('Output power cannot be lower or greater than generator power.')
        return output_power

    def _calculate_energy_data(self, device: Device, weather_raports: Search) -> Dict[str, float]:
        """Calculate energy generated by the device in a given time.

        Arguments:
        device -- instance of a device for calculating energy generation for
        device_raports -- device power raports filtered by elasticsearch 
        """
        # for photovoltaics searching in device raports about time intervals it's not neccesary because pv is always work (acumulators not)
        # maybe we should divide generators for two cases: acumulators and PV's or implement logic for generate energy by acu in EnergyStorageCalculator
        
        # in our code each device has room and state - this convention imo is wrong (PV is not placed in the room, and is always ON)
       
        sum_of_energy_in_kwh = 0.0
        for raport in weather_raports:
            #we need time intervals with a specific solar radiation intensity value, e.g.:
            #01.01.2022 16:00:00 - 01.01.2022 18:00:00 was the value of x, otherwise we cannot calculate it
            if raport.datetime_to is None:
                datetime_to = datetime.now
            else:
                datetime_to = raport.datetime_to
            diff_in_hours = self._calculate_difference_in_time(raport.datetime_from, datetime_to)
            solar_radiation_coefficient = self._get_weather_coefficient(raport.solar_radiation, self.min_solar_radiation, self.max_solar_radiation)
            output_power = self._calculate_power_of_photovoltaic(solar_radiation_coefficient, device.energy_generation)
            output_power_in_kwh = output_power / 1000 * diff_in_hours #think about rounding this factor 
            sum_of_energy_in_kwh += output_power_in_kwh

        return {"energy_generated": sum_of_energy_in_kwh}

        
class EnergyStorageCalculator(EnergyCalculator):
    """Energy calculating class for energy storing devices"""

    def _calculate_energy_data(self, device: Device, device_raports: Search) -> Dict[str, float]:
        """Calculate energy stored by the device in a given time.

        Arguments:
        device -- instance of a device for calculating energy storage for
        device_raports -- device power raports filtered by elasticsearch 
        """
        for raport in device_raports:
            print(raport.device, raport.turned_on, device.energy_consumption)

        energy_stored = "not_calculated_yet"
        return {"energy_stored": energy_stored}
