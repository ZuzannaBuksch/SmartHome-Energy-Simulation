from datetime import datetime

from django.test import TestCase
from django.urls import reverse_lazy
from mock import patch
from rest_framework.test import APIClient
from users.models import User

from .models import (Building, ChargeStateRaport, DeviceRaport,
                     EnergyGenerator, EnergyReceiver, EnergyStorage,
                     StorageChargingAndUsageRaport, WeatherRaport)
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
        """Energy consumed by single device is calculated correctly"""

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
        
        hour_08_00 = self.get_date_from_string("2022-03-30 08:00:00")
        hour_10_30 = self.get_date_from_string("2022-03-30 10:30:00")
        hour_11_00 =  self.get_date_from_string("2022-03-30 11:00:00")
        hour_11_30 =  self.get_date_from_string("2022-03-30 11:30:00")
        hour_12_00 = self.get_date_from_string("2022-03-30 12:00:00")
        hour_12_15 =  self.get_date_from_string("2022-03-30 12:15:00")
        hour_12_30 = self.get_date_from_string("2022-03-30 12:30:00")
     
        WeatherRaport.objects.create(datetime_from=hour_10_30, datetime_to=hour_11_00, solar_radiation=340.0, temperature=10.5, wind_speed=5.8)
        WeatherRaport.objects.create(datetime_from=hour_11_00, datetime_to=hour_12_00, solar_radiation=360.0, temperature=10.5, wind_speed=4.0)
        WeatherRaport.objects.create(datetime_from=hour_12_00, datetime_to=hour_12_15, solar_radiation=410.0, temperature=11.0, wind_speed=5.2)
        WeatherRaport.objects.create(datetime_from=hour_12_15,  solar_radiation=312.0, temperature=11.5, wind_speed=5.8)
 
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": hour_08_00, "end_date": hour_12_30})
            building_devices = response.data.get("building_devices", [])
            energy_generated = round(building_devices[0].get("energy_generated"), 6)
            self.assertEqual(energy_generated, 0.428609) # 0.1025525 + 0.21717 + 0.061833125 + 0.0470535 = 0.428609125

            response = self.client.get(url, data={"start_date": hour_11_30, "end_date": hour_12_30})
            building_devices = response.data.get("building_devices", [])
            energy_generated = round(building_devices[0].get("energy_generated"), 6)
            self.assertEqual(energy_generated, 0.217472) # 0.108585 + 0.061833125 + 0.0470535 = 0.217471625


    def setUpEnergyStorageCharging(self):
        user = User.objects.create(email="user@email.com", password="defaultpassword")
        building = Building.objects.create(user=user, name="house")
        energy_storage = EnergyStorage.objects.create(name='storage1', building=building, capacity = 200, battery_voltage = 24) #4800 Wh -> 4.8 kWh
        return {
            "building": building,
            "devices": [energy_storage]
        }

    def test_calculate_stored_energy_charging(self):
        """Energy stored is calculated correctly"""
        db = self.setUpEnergyStorageCharging()
        building = db["building"]
        device = db["devices"][0]

        hour_08_00 = self.get_date_from_string("2022-03-30 08:00:00")
        hour_10_30 = self.get_date_from_string("2022-03-30 10:30:00")
        hour_11_30 = self.get_date_from_string("2022-03-30 11:30:00")
        hour_11_00 = self.get_date_from_string("2022-03-30 11:00:00")
        hour_12_00 = self.get_date_from_string("2022-03-30 12:00:00")

        ChargeStateRaport.objects.create(device = device, charge_value = 0.0, date = hour_10_30)
        ChargeStateRaport.objects.create(device = device, charge_value = 4.0, date = hour_11_30)
        ChargeStateRaport.objects.create(device = device, charge_value = 2.0, date = hour_11_00)

        EnergyReceiver.objects.create(building=building, name="bulb3", state=False, device_power=70, supply_voltage=8)
        StorageChargingAndUsageRaport.objects.create(date_time_from = hour_11_00, date_time_to = hour_12_00, device = device, job_type = 'CH')
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": hour_08_00, "end_date": hour_12_00})
            building_devices = response.data.get("building_devices", [])
            energy_stored = round(building_devices[0].get("energy_stored"), 6)
            self.assertEqual(energy_stored, 4.48 * 0.95)
            
    
    def test_calculate_stored_energy_usage(self):
        """Energy stored is calculated correctly"""
        db = self.setUpEnergyStorageCharging()
        building = db["building"]
        device = db["devices"][0]

        hour_08_00 = self.get_date_from_string("2022-01-29 08:00:00")
        hour_10_30 = self.get_date_from_string("2022-03-30 10:30:00")
        hour_11_30 = self.get_date_from_string("2022-03-30 11:30:00")
        hour_11_00 = self.get_date_from_string("2022-03-30 11:00:00")
        hour_12_00 = self.get_date_from_string("2022-03-30 12:00:00")

        ChargeStateRaport.objects.create(device = device, charge_value = 0.0, date = hour_10_30)
        ChargeStateRaport.objects.create(device = device, charge_value = 4.0, date = hour_11_30)
        ChargeStateRaport.objects.create(device = device, charge_value = 2.0, date = hour_11_00)

        receiver = EnergyReceiver.objects.create(building=building, name="bulb3", state=False, device_power=70, supply_voltage=8)
        StorageChargingAndUsageRaport.objects.create(date_time_from = hour_11_00, date_time_to = hour_12_00, device = device, energy_receiver = receiver, job_type = 'US')
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked
            response = self.client.get(url, data={"start_date": hour_08_00, "end_date": hour_12_00})
            building_devices = response.data.get("building_devices", [])
            energy_stored = round(building_devices[0].get("energy_stored"), 6)
            self.assertEqual(energy_stored, round(3.93 * 0.95, 6))
            
    def test_calculate_stored_energy_usage_and_charging(self):
        """Energy stored is calculated correctly"""
        db = self.setUpEnergyStorageCharging()
        building = db["building"]
        device = db["devices"][0]

        hour_08_00 = self.get_date_from_string("2022-03-30 08:00:00")
        hour_10_30 = self.get_date_from_string("2022-03-30 10:30:00")
        hour_11_00 = self.get_date_from_string("2022-03-30 11:00:00")
        hour_11_15 = self.get_date_from_string("2022-03-30 11:15:00") # diff = 0.75
        hour_12_00 = self.get_date_from_string("2022-03-30 12:00:00") # diff = 0.5
        hour_15_45 = self.get_date_from_string("2022-03-30 15:45:00") # diff = 3.75
        hour_16_00 = self.get_date_from_string("2022-03-30 16:00:00")
        hour_19_00 = self.get_date_from_string("2022-03-30 19:00:00") # diff = 3.25

        ChargeStateRaport.objects.create(device = device, charge_value = 50.0, date = hour_10_30)
        receiver = EnergyReceiver.objects.create(building=building, name="bulb1", state=False, device_power=40, supply_voltage=8)
        receiver2 =EnergyReceiver.objects.create(building=building, name="bulb2", state=False, device_power=50, supply_voltage=8)

        StorageChargingAndUsageRaport.objects.create(date_time_from = hour_10_30, date_time_to = hour_12_00, device = device, energy_receiver = receiver, job_type = 'US')
        StorageChargingAndUsageRaport.objects.create(date_time_from = hour_11_15, date_time_to = hour_15_45, device = device, energy_receiver = receiver2, job_type = 'US')
        
        StorageChargingAndUsageRaport.objects.create(date_time_from = hour_15_45,  device = device, job_type = 'CH')

        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked

            response = self.client.get(url, data={"start_date": hour_11_00, "end_date": hour_16_00})
            building_devices = response.data.get("building_devices", [])
            energy_stored = round(building_devices[0].get("energy_stored"), 6)
            self.assertEqual(energy_stored, round(49.855* 0.95 , 6))


    def setUpSingleHRManyDForDatesTests(self):
        """Single HR - House, Room; Many Devices"""
        
        user = User.objects.create(email="defaultuser@email.com", password="defaultpassword")
        building = Building.objects.create(user=user, name="house3")
        device_1 = EnergyReceiver.objects.create(building=building, name="bulb1", state=False, device_power=60, supply_voltage=8)
        device_2 = EnergyReceiver.objects.create(building=building, name="bulb2", state=False, device_power=60, supply_voltage=8)
        energy_generator = EnergyGenerator.objects.create(name='photovoltaics', building=building, generation_power = 635.0)
        return {
            "building": building,
            "devices": [device_1, device_2, energy_generator]
        }

    def test_calculate_single_HRD_consumption_without_turned_off_date(self):
        db = self.setUpSingleHRManyDForDatesTests()
        building = db["building"]
        device = db["devices"][0]
        
        hour_07 = self.get_date_from_string("2022-03-30 07:00:00")
        hour_08 = self.get_date_from_string("2022-03-30 08:00:00")
        hour_09 = self.get_date_from_string("2022-03-30 09:00:00")
        hour_09_30 = self.get_date_from_string("2022-03-30 09:30:00")
        hour_10 = self.get_date_from_string("2022-03-30 10:00:00")
        hour_11 = self.get_date_from_string("2022-03-30 11:00:00")
        hour_12 = self.get_date_from_string("2022-03-30 12:00:00")
        hour_12_30 = self.get_date_from_string("2022-03-30 12:30:00")
        hour_15_45 = self.get_date_from_string("2022-03-30 15:45:00")

        DeviceRaport.objects.create(device=device, turned_on=hour_09, turned_off=hour_10)
        DeviceRaport.objects.create(device=device, turned_on=hour_11)
        
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked

            #---|start_date 10:30|---|ON 11:00|---|end_date 12:00|---|OFF None|
            response = self.client.get(url, data={"start_date": hour_10, "end_date": hour_12})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[0].get("energy_consumed")
            self.assertEqual(energy, 0.06) #(60 W / 1000) * 1 h

            #---|ON 11:00|---|start_date 12:30|---|end_date 12:30|---|OFF None|
            response = self.client.get(url, data={"start_date": hour_12_30, "end_date": hour_15_45})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[0].get("energy_consumed")
            self.assertEqual(energy, 0.195) #(60 W / 1000) * 3.25 h

            #---|start_date 07:00|---|end_date 08:00|---|ON 09:00|-----
            response = self.client.get(url, data={"start_date": hour_07, "end_date": hour_08})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[0].get("energy_consumed")
            self.assertEqual(energy, 0.0) #(60 W / 1000) * 0 h

            #---|start_date 07:00|---|ON 09:00|---|OFF 10:00|---|end_date 11:00|---|ON 11:00|
            response = self.client.get(url, data={"start_date": hour_07, "end_date": hour_11})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[0].get("energy_consumed")
            self.assertEqual(energy, 0.06) #(60 W / 1000) * 1 h

            #---|ON 09:00|---|start_date 09:30|---|OFF 10:00|---|ON 11:00|---|end_date 15:45|
            response = self.client.get(url, data={"start_date": hour_09_30, "end_date": hour_15_45})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[0].get("energy_consumed")
            self.assertEqual(energy, 0.315) #(60 W / 1000) * 5.25 h

    def test_filter_raports_by_device_and_date(self):
        db = self.setUpSingleHRManyDForDatesTests()
        building = db["building"]
        device = db["devices"][1]
        
        hour_07 = self.get_date_from_string("2022-03-30 07:00:00")
        hour_08 = self.get_date_from_string("2022-03-30 08:00:00")
        hour_09_30 = self.get_date_from_string("2022-03-30 09:30:00")
        hour_11 = self.get_date_from_string("2022-03-30 11:00:00")
        hour_12_30 = self.get_date_from_string("2022-03-30 12:30:00")
        hour_15_45 = self.get_date_from_string("2022-03-30 15:45:00")

        DeviceRaport.objects.create(device=device, turned_on=hour_07, turned_off=hour_15_45)
        
        with patch.object(BuildingEnergyView, 'get_object', return_value=building):
            url = reverse_lazy('smarthome:energy', kwargs={'pk': 0}) #pk can by anything, the building is already mocked

            response = self.client.get(url, data={"start_date": hour_08, "end_date": hour_12_30})
            building_devices = response.data.get("building_devices", [])
            energy = building_devices[1].get("energy_consumed")
            self.assertEqual(energy, 0.27) #(60 W / 1000) * 4.5 h

            response = self.client.get(url, data={"start_date": hour_08, "end_date": hour_09_30})
            building_devices = response.data.get("building_devices", [])
            energy1 = building_devices[1].get("energy_consumed")

            response = self.client.get(url, data={"start_date": hour_09_30, "end_date": hour_11})
            building_devices = response.data.get("building_devices", [])
            energy2 = building_devices[1].get("energy_consumed")

            response = self.client.get(url, data={"start_date": hour_11, "end_date": hour_12_30})
            building_devices = response.data.get("building_devices", [])
            energy3 = building_devices[1].get("energy_consumed")

            total_energy = energy1 + energy2 + energy3
            self.assertEqual(total_energy, energy) 



