import re
from abc import ABC
from datetime import datetime, timedelta
from typing import Dict
from xmlrpc.client import DateTime

from django.forms.models import model_to_dict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

from .documents import (ChargeStateDocument, DeviceRaportDocument,
                        StorageChargingAndUsageDocument, WeatherDocument)
from .models import (Device, DeviceRaport, EnergyGenerator, EnergyReceiver,
                     StorageChargingAndUsageRaport, ChargeStateRaport)

client = Elasticsearch()

class DeviceCalculateManager():
    """Manager class for choosing strategy for calculating device energy data"""

    def get_device_energy(self, device: Device, start_date: datetime=None) -> dict:
        device_type = {
            "EnergyReceiver": EnergyReceiverCalculator,
            "EnergyGenerator": EnergyGeneratorCalculator,
            "EnergyStorage": EnergyStorageCalculator,
        }.get(device.type)
        return device_type().get_device_energy_calculation(device, start_date)

class EnergyCalculator(ABC):
    """Abstract class that provides interface with methods for concrete energy calculators"""

    def _filter_storage_raports_by_device_and_date(self, device: Device, start_date: datetime=None) -> Search:
        raports = StorageChargingAndUsageDocument.search().query('match', device__id=device.id)
        if start_date:
            raports = raports.filter("range", turned_on={"gte": start_date})
        return raports

    def _filter_charge_state_raports_by_device_and_date(self, device: Device, start_date: datetime=None) -> Search:
        raports = ChargeStateDocument.search().query('match', device__id=device.id)
        if start_date:
            raports = raports.filter("range", turned_on={"gte": start_date})
        return raports
    
    def _filter_raports_by_device_and_date(self, device: Device, start_date: datetime=None) -> Search:
        raports = DeviceRaportDocument.search().query('match', device__id=device.id)
        if start_date:
            raports = raports.filter("range", turned_on={"gte": start_date})
        return raports
    
    def _filter_weather_raports_by_date(self, start_date: datetime=None) -> Search:
        raports = WeatherDocument.search()
        if start_date:
            raports = raports.filter("range", datetime_from={"gte": start_date})
        return raports

    def _calculate_difference_in_time(self, turned_on: datetime, turned_off: datetime) -> float:
        diff = turned_off - turned_on
        diff_in_hours = diff.total_seconds() / 3600
        return diff_in_hours
        
class EnergyReceiverCalculator(EnergyCalculator):
    """Energy calculating class for energy receiving devices"""

    def get_device_energy_calculation(self, device: Device, start_date: datetime=None) -> dict:
        device_raports = self._filter_raports_by_device_and_date(device, start_date)
        return {
            **model_to_dict(device),
            **self._calculate_energy_data(device, device_raports),
        }

    def _calculate_energy_data(self, device: Device, device_raports: Search) -> Dict[str, float]:
        """Calculate energy consumptioned by the device in a given time.

        Arguments:
        device -- instance of a device for calculating energy consumption for
        device_raports -- device power raports filtered by elasticsearch 
        """
        sum_of_hours = 0.0
        for raport in device_raports:
            if raport.turned_off is None:
                turned_off = datetime.now()
            else:
                turned_off = raport.turned_off
            diff_in_hours = self._calculate_difference_in_time(raport.turned_on, turned_off)
            sum_of_hours += diff_in_hours

        kwh_factor = device.device_power / 1000 * sum_of_hours #think about rounding this factor 
        return {"energy_consumed": kwh_factor}

class EnergyGeneratorCalculator(EnergyCalculator):
    """Energy calculating class for energy generating devices"""

    #-------------------------calculations only for PV's----------------------------------
    #     # raports = WeatherDocument.filter("range", turned_on={"gte": start_date}) what if there will be a start date in reports, e.g.:
    # ... 16:05:00, 16:04:30, 16:05:30 ... and we are interested in e.g. "start_date" = 16:04.51 

    min_solar_radiation = 0 #W/m^2
    max_solar_radiation = 1000 #W/m^2
    new_min_range = 0
    new_max_range = 1
    weather_loss_factor = 0.05

    def get_device_energy_calculation(self, device: Device, start_date: datetime=None) -> dict:
        weather_raports = self._filter_weather_raports_by_date(start_date)
        return {
            **model_to_dict(device),
            **self._calculate_energy_data(device, weather_raports),
        }

    def _get_weather_coefficient(self, solar_radiation: float, min_range: int, max_range: int):
        weight = ((solar_radiation - self.min_solar_radiation) / (self.max_solar_radiation - self.min_solar_radiation)) * (max_range - min_range) + min_range
        return weight
    
    def _calculate_power_of_photovoltaic(self, solar_radiation_coefficient: float, generator_power: float):
        output_power = generator_power * (solar_radiation_coefficient + self.weather_loss_factor)
        if output_power > generator_power or output_power < 0.0:
            raise ValueError('Output power cannot be lower or greater than generator power.')
        return output_power

    def _calculate_energy_data(self, device: Device, weather_raports: Search) -> Dict[str, float]:
        """Calculate energy generated by the device in a given time.

        Arguments:
        device -- instance of a device for calculating energy generation for
        device_raports -- device power raports filtered by elasticsearch 
        """
        sum_of_energy_in_kwh = 0.0
        for raport in weather_raports:
            if raport.datetime_to is None:
                datetime_to = datetime.now()
            else:
                datetime_to = raport.datetime_to
            diff_in_hours = self._calculate_difference_in_time(raport.datetime_from, datetime_to)
            solar_radiation_coefficient = self._get_weather_coefficient(raport.solar_radiation, self.new_min_range, self.new_max_range)
            output_power = self._calculate_power_of_photovoltaic(solar_radiation_coefficient, device.generation_power)
            output_power_in_kwh = output_power / 1000 * diff_in_hours #think about rounding this factor 
            sum_of_energy_in_kwh += output_power_in_kwh
        return {"energy_generated": sum_of_energy_in_kwh}
    
class EnergyStorageCalculator(EnergyCalculator):
    """Energy calculating class for energy storing devices"""

    charging_current_factor = 0.1
    charging_loss_factor = 0.05

    def get_device_energy_calculation(self, device: Device, start_date: datetime=None) -> dict:
        storage_raports = self._filter_storage_raports_by_device_and_date(device, start_date)
        charge_state_raports = self._filter_charge_state_raports_by_device_and_date(device, start_date)
        return {
            **model_to_dict(device),
            **self._calculate_energy_data(device, storage_raports, charge_state_raports),
        }

    def _calculate_energy_data(self, device: Device, storage_charging_and_usage_raport: Search, charge_state_raports: Search) -> Dict[str, float]:

        last_index = charge_state_raports.count() -1  # we are interested the last charge state
        last_charge_state = charge_state_raports.execute()[last_index].charge_value #kwh
        charging_current = self.charging_current_factor * device.capacity #assumption, charging current always equals 10% capacity of storage [A]
        actual_charge_state = last_charge_state

        for raport in storage_charging_and_usage_raport:
            if not raport.date_time_to:
                datetime_to = datetime.now()
            else:
                datetime_to = raport.date_time_to

            diff_in_hours = self._calculate_difference_in_time(raport.date_time_from, datetime_to)

            if not raport.energy_receiver:
                print('charging')
                additional_capacity = (charging_current * device.battery_voltage * diff_in_hours) / 1000 #[kWh]

                if actual_charge_state + additional_capacity <= device.capacity: #important thing! imo this condition should be at all time controlled by energy management system
                    actual_charge_state += additional_capacity
                else:
                    raise ValueError('Accumulated energy cannot be greater than storage capacity')

            else:
                print('usage')
                # receiver_power = raport.energy_receiver.device_power
                # capacity_loss = receiver_power * diff_in_hours
                # if actual_charge_state - capacity_loss >= device.capacity:
                #     actual_charge_state -= capacity_loss
                # else:
                #     raise ValueError('Accumulated energy cannot be less than storage capacity')

                #in energy management system should be system of control max out current e.g. 
                #sum of out current to supply receivers shouldn't be more than 5* capacity of storage
                #jak rozkminic sytuacje, gdy wiele urzadzen pobiera prad z generatora? trzeba gdzies dac zabezpieczenie ze nie moze byc
                #za duze obciazenie akumulatora plus gdzie bedzie sprawdzane czy akumulator ma w ogole tyle zgromadzonej energii

        #how to create real raport in the database?
        actual_charge_state = actual_charge_state - self.charging_loss_factor * actual_charge_state
        return {"energy_stored": actual_charge_state}
