from mock import patch
from datetime import datetime
from django.urls import reverse_lazy
from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User

from .models import Building, DeviceRaport, EnergyGenerator, EnergyReceiver, WeatherRaport, EnergyStorage, ChargeStateRaport, StorageChargingAndUsageRaport

from .views import BuildingEnergyView

class EnergyTestCase(TestCase):
    client = APIClient()

    def get_date_from_string(self, date):
        date_format_str = '%Y-%m-%d %H:%M:%S'
        return datetime.strptime(date, date_format_str)

    def setUpSingleHRD(self):
        """Single HRD - House, Room, Device"""
        user = User.objects.create(email="defaultuser@email.com", password="defaultpassword")
        building = Building.objects.create(user=user, name="house")
        energy_receiver = EnergyReceiver.objects.create(building=building, name="bulb", state=False, device_power=60, supply_voltage=8)
        return {
            "building": building,
            "devices": [energy_receiver]
        }


    def test_calculate_single_HRD_consumption_right(self):
        """Energy consumped by single device is calculated correctly"""

        db = self.setUpSingleHRD()
        building = db["building"]
        device = db["devices"][0]
        turned_on = self.get_date_from_string("2022-03-30 00:00:00")
        turned_off = self.get_date_from_string("2022-03-31 00:00:00") #24 hours difference
        start_date = '2022-03-29 10:02:01'
        DeviceRaport.objects.create(id=0, device=device, turned_on=turned_on, turned_off=turned_off)
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": start_date})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[0].get("energy_consumed")
            self.assertEqual(len(building_devices), 1)
            self.assertEqual(energy, 1.44) #(60 W / 1000) * 24 h


    def setUpSingleHRManyD(self):
        """Single HR - House, Room; Many Devices"""
        
        user = User.objects.create(email="defaultuser@email.com", password="defaultpassword")
        building = Building.objects.create(user=user, name="house2")
        device_1 = EnergyReceiver.objects.create(building=building, name="bulb1", state=False, device_power=50, supply_voltage=8)
        device_2 = EnergyReceiver.objects.create(building=building, name="bulb2", state=False, device_power=60, supply_voltage=8)
        device_3 = EnergyReceiver.objects.create(building=building, name="bulb3", state=False, device_power=70, supply_voltage=8)
        return {
            "building": building,
            "devices": [device_1, device_2, device_3]
        }

    def test_calculate_singleHR_many_device_energy_consumption_right(self):
        """Energy consumped by many devices in single house is calculated correctly"""

        db = self.setUpSingleHRManyD()
        building = db["building"]
        devices = db["devices"]

        start_date = '2022-01-29 08:00:00'

        turned_on_1 = self.get_date_from_string("2022-03-30 12:00:00")
        turned_off_1 =  self.get_date_from_string("2022-03-30 12:30:00") #diff = 0.5

        turned_on_2 = self.get_date_from_string("2022-03-30 12:00:00")
        turned_off_2 =  self.get_date_from_string("2022-03-30 14:30:00") #diff = 2.5

        turned_on_3 = self.get_date_from_string("2022-03-30 10:00:00")
        turned_off_3 =  self.get_date_from_string("2022-03-30 18:30:00") #diff = 8.5

        turned_on_4 = self.get_date_from_string("2022-03-30 16:30:00")
        turned_off_4 =  self.get_date_from_string("2022-03-30 18:30:00") #diff = 2

        DeviceRaport.objects.create(device=devices[0], turned_on=turned_on_1, turned_off=turned_off_1)
        DeviceRaport.objects.create(device=devices[1], turned_on=turned_on_2, turned_off=turned_off_2)
        DeviceRaport.objects.create(device=devices[2], turned_on=turned_on_3, turned_off=turned_off_3)
        DeviceRaport.objects.create(device=devices[0], turned_on=turned_on_4, turned_off=turned_off_4)
        DeviceRaport.objects.create(device=devices[1], turned_on=turned_on_4, turned_off=turned_off_4)

        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": start_date})
            building_devices = response.data.get("building_devices", [])
            energy_1 = round(building_devices[0].get("energy_consumed"), 6) #0.125000
            energy_2 = round(building_devices[1].get("energy_consumed"), 6) #0.270000
            energy_3 = round(building_devices[2].get("energy_consumed"), 6) #0.595000
            sum_of_energy = energy_1 + energy_2 + energy_3

            self.assertEqual(len(building_devices), 3)
            self.assertEqual(energy_1, 0.125000) 
            self.assertEqual(energy_2, 0.270000)
            self.assertEqual(energy_3, 0.595000)
            #self.assertEqual(energy_3, 0.595) #be careful because sometimes there is rounding like this (AssertionError: 0.5950000000000001 != 0.595) -> it can be corrected and write tests 
            self.assertEqual(sum_of_energy, 0.99) #0.125 + 0.27 + 0.595 = 0.99
        

    def setUpEnergyGenerator(self):
        user = User.objects.create(email="user@email.com", password="defaultpassword")
        building = Building.objects.create(user=user, name="house")
        energy_generator = EnergyGenerator.objects.create(name='photovoltaics1', building=building, generation_power = 635.0)
        return {
            "building": building,
            "devices": [energy_generator]
        }
   
    def test_calculate_generated_energy(self):
        """Energy generated is calculated correctly"""
        db = self.setUpEnergyGenerator()
        building = db["building"]
        
        start_date = '2022-01-29 08:00:00'

        datetime_1 = self.get_date_from_string("2022-03-30 10:30:00")
        datetime_2 =  self.get_date_from_string("2022-03-30 11:00:00")
        datetime_3 = self.get_date_from_string("2022-03-30 12:00:00")
        datetime_4 =  self.get_date_from_string("2022-03-30 12:15:00")
        datetime_5 = self.get_date_from_string("2022-03-30 12:30:00")
     
        WeatherRaport.objects.create(datetime_from=datetime_1, datetime_to=datetime_2, solar_radiation=340.0, temperature=10.5, wind_speed=5.8)
        WeatherRaport.objects.create(datetime_from=datetime_2, datetime_to=datetime_3, solar_radiation=360.0, temperature=10.5, wind_speed=4.0)
        WeatherRaport.objects.create(datetime_from=datetime_3, datetime_to=datetime_4, solar_radiation=410.0, temperature=11.0, wind_speed=5.2)
        WeatherRaport.objects.create(datetime_from=datetime_4, datetime_to=datetime_5, solar_radiation=312.0, temperature=11.5, wind_speed=5.8)
 
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": start_date})
            building_devices = response.data.get("building_devices", [])
            energy_generated = round(building_devices[0].get("energy_generated"), 6)

        self.assertEqual(energy_generated, 0.514667) # 0.123825 + 0.26035 + 0.073025 + 0.0574675 = 0.5146675

    def setUpEnergyStorageCharging(self):
        user = User.objects.create(email="user@email.com", password="defaultpassword")
        building = Building.objects.create(user=user, name="house")
        energy_storage = EnergyStorage.objects.create(name='storage1', building=building, capacity = 200 , battery_voltage = 24) #4800 Wh -> 4.8 kWh
        return {
            "building": building,
            "devices": [energy_storage]
        }

    def test_calculate_stored_energy_charging(self):
        """Energy stored is calculated correctly"""
        db = self.setUpEnergyStorageCharging()
        building = db["building"]
        device = db["devices"][0]

        start_date = '2022-01-29 08:00:00'

        datetime_1 = self.get_date_from_string("2022-03-30 10:30:00")
        datetime_2 = self.get_date_from_string("2022-03-30 11:30:00")
        datetime_3 = self.get_date_from_string("2022-03-30 11:00:00")
        datetime_4 = self.get_date_from_string("2022-03-30 12:00:00")

        ChargeStateRaport.objects.create(device = device, charge_value = 0.0, date = datetime_1)
        ChargeStateRaport.objects.create(device = device, charge_value = 4.0, date = datetime_2)
        ChargeStateRaport.objects.create(device = device, charge_value = 2.0, date = datetime_3)

        EnergyReceiver.objects.create(building=building, name="bulb3", state=False, device_power=70, supply_voltage=8)
        StorageChargingAndUsageRaport.objects.create(date_time_from = datetime_3, date_time_to = datetime_4, device = device, job_type = 'CH')
        
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": start_date})
            building_devices = response.data.get("building_devices", [])
            energy_stored = round(building_devices[0].get("energy_stored"), 6)
            self.assertEqual(energy_stored, 4.48 * 0.95)
    
    def test_calculate_stored_energy_usage(self):
        """Energy stored is calculated correctly"""
        db = self.setUpEnergyStorageCharging()
        building = db["building"]
        device = db["devices"][0]

        start_date = '2022-01-29 08:00:00'

        datetime_1 = self.get_date_from_string("2022-03-30 10:30:00")
        datetime_2 = self.get_date_from_string("2022-03-30 11:30:00")
        datetime_3 = self.get_date_from_string("2022-03-30 11:00:00")
        datetime_4 = self.get_date_from_string("2022-03-30 12:00:00")

        ChargeStateRaport.objects.create(device = device, charge_value = 0.0, date = datetime_1)
        ChargeStateRaport.objects.create(device = device, charge_value = 4.0, date = datetime_2)
        ChargeStateRaport.objects.create(device = device, charge_value = 2.0, date = datetime_3)

        receiver = EnergyReceiver.objects.create(building=building, name="bulb3", state=False, device_power=70, supply_voltage=8)
        StorageChargingAndUsageRaport.objects.create(date_time_from = datetime_3, date_time_to = datetime_4, device = device, energy_receiver = receiver, job_type = 'US')
        
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": start_date})
            building_devices = response.data.get("building_devices", [])
            energy_stored = round(building_devices[0].get("energy_stored"), 6)
            self.assertEqual(energy_stored, round(3.93 * 0.95, 6))

