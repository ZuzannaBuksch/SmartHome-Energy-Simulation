import re
from abc import ABC
from copy import deepcopy
from datetime import datetime, timedelta
from os import PRIO_USER
from pprint import pprint
from typing import Dict
from xmlrpc.client import DateTime

from django.forms.models import model_to_dict
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from elasticsearch_dsl.query import Q

from .documents import (ChargeStateDocument, DeviceRaportDocument,
                        StorageChargingAndUsageDocument, WeatherDocument)
from .models import (ChargeStateRaport, Device, DeviceRaport, EnergyGenerator,
                     EnergyReceiver, StorageChargingAndUsageRaport)

client = Elasticsearch()

class DeviceCalculateManager():
    """Manager class for choosing strategy for calculating device energy data"""

    def get_device_energy(self, device: Device, start_date: datetime=None, end_date: datetime=None) -> dict:
        device_type = {
            "EnergyReceiver": EnergyReceiverCalculator,
            "EnergyGenerator": EnergyGeneratorCalculator,
            "EnergyStorage": EnergyStorageCalculator,
        }.get(device.type)
        return device_type().get_device_energy_calculation(device, start_date, end_date)

class EnergyCalculator(ABC):
    """Abstract class that provides interface with methods for concrete energy calculators"""

    def _filter_storage_raports_by_device_and_date(self, device: Device, start_date: datetime=None) -> Search:
        raports = StorageChargingAndUsageDocument.search().query('match', device__id=device.id)
        if start_date:
            raports = raports.filter("range", date_time_from={"gte": start_date})
        return raports

    def _filter_charge_state_raports_by_device_and_date(self, device: Device, start_date: datetime=None) -> Search:
        raports = ChargeStateDocument.search().query('match', device__id=device.id)
        if start_date:
            raports = raports.filter("range", date={"gte": start_date})
        return raports
        
    def _filter_raports_by_device_and_date(self, device: Device, start_date: datetime, end_date: datetime = None) -> Search:
        if not end_date:
            end_date = datetime.now()
        raports = DeviceRaportDocument.search().query('match', device__id=device.id)
        query_filter = raports.filter(
                Q("range", turned_on={"gte": start_date, "lte": end_date}) |
                Q("range", turned_off={"gte": start_date, "lte": end_date}) |
                Q(
                    Q("range", turned_on={"lt": start_date}) &
                    Q("range",  turned_off = {"gt": end_date})

                ) |
                Q(
                    Q("range", turned_on={"lt": end_date}) &
                    ~Q("exists", field='turned_off')
                )
        )
        response = query_filter.execute()
        for raport in response:
            if raport.turned_off:
                raport.turned_off = end_date if raport.turned_off > end_date else raport.turned_off
            else:
                raport.turned_off = end_date
            raport.turned_on = start_date if raport.turned_on < start_date else raport.turned_on
        return response
    
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

    def get_device_energy_calculation(self, device: Device, start_date: datetime=None, end_date: datetime=None) -> dict:
        device_raports = self._filter_raports_by_device_and_date(device, start_date, end_date)
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
            diff_in_hours = self._calculate_difference_in_time(raport.turned_on, raport.turned_off)
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

    def get_device_energy_calculation(self, device: Device, start_date: datetime=None, end_date: datetime=None) -> dict:
        # TODO: Add end date to filter weather raports
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
        # TODO: Add rounding calculated values
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

    def get_device_energy_calculation(self, device: Device, start_date: datetime=None, end_date: datetime=None) -> dict:
        # TODO: Add end date to filter storage raports and charge state raports
        storage_raports = self._filter_storage_raports_by_device_and_date(device, start_date)
        charge_state_raports = self._filter_charge_state_raports_by_device_and_date(device, start_date)
        return {
            **model_to_dict(device),
            **self._calculate_energy_data(device, storage_raports, charge_state_raports),
        }

    def _calculate_energy_data(self, device: Device, storage_charging_and_usage_raport: Search, charge_state_raports: Search) -> Dict[str, float]:
        # TODO: Add rounding calculated values
        charge_state_raports = charge_state_raports.sort({"date" : {"order" : "asc"}})
        last_charge_state = charge_state_raports.execute()[-1].charge_value #kwh
        charging_current = self.charging_current_factor * device.capacity #assumption, charging current always equals 10% capacity of storage [A]
        actual_charge_state = last_charge_state
        
        for raport in storage_charging_and_usage_raport:
            if not raport.date_time_to:
                datetime_to = datetime.now()
            else:
                datetime_to = raport.date_time_to

            diff_in_hours = self._calculate_difference_in_time(raport.date_time_from, datetime_to)

            if raport.job_type == 'CH':
                additional_capacity = (charging_current * device.battery_voltage * diff_in_hours) / 1000 #[kWh]
                if actual_charge_state + additional_capacity <= device.capacity: #important thing! imo this condition should be at all time controlled by energy management system
                    actual_charge_state += additional_capacity
                else:
                    raise ValueError('Accumulated energy cannot be greater than storage capacity')

            elif raport.job_type == 'US':
                receiver_power = raport.energy_receiver.device_power
                capacity_loss = (receiver_power * diff_in_hours) / 1000
                if actual_charge_state - capacity_loss >= 0.0:
                    actual_charge_state -= capacity_loss
                else:
                    raise ValueError('Accumulated energy cannot be less than storage capacity')

                #in energy management system should be system of control max out current e.g. 
                #sum of out current to supply receivers shouldn't be more than 5* capacity of storage
                #jak rozkminic sytuacje, gdy wiele urzadzen pobiera prad z generatora? trzeba gdzies dac zabezpieczenie ze nie moze byc
                #za duze obciazenie akumulatora plus gdzie bedzie sprawdzane czy akumulator ma w ogole tyle zgromadzonej energii

        # TODO: Create ChargeStateRaport
        actual_charge_state = actual_charge_state * (1- self.charging_loss_factor)
        return {"energy_stored": actual_charge_state}
