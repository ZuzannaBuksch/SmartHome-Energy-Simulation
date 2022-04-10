from datetime import datetime

from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User

from .models import Building, DeviceRaport, EnergyReceiver, Room


class EnergyTestCase(TestCase):
    client = APIClient()

    def setUpSingleHRD(self):
        """Single HRD - House, Room, Device"""

        user = User.objects.create(id=0, email="defaultuser@email.com", password="defaultpassword")
        building = Building.objects.create(id=0, user=user, name="house")
        room = Room.objects.create(id=0, building=building, name="kitchen", area=50)
        return EnergyReceiver.objects.create(id=0, room=room, name="bulb", state=False, energy_consumption=60)
        
    def test_calculate_single_HRD_consumption_right(self):
        """Energy consumped by single device is calculated correctly"""

        device = self.setUpSingleHRD()
        turned_on = self.get_date_from_string("2022-03-30 00:00:00")
        turned_off =  self.get_date_from_string("2022-03-31 00:00:00") #24 hours difference
        DeviceRaport.objects.create(id=0, device=device, turned_on=turned_on, turned_off=turned_off)
        response = self.client.get('/api/buildings/0/energy/', format='json')
        building_rooms = response.data.get("building_rooms", [])
        room_devices = building_rooms[0].get("room_devices",[])
        energy = room_devices[0].get("energy_consumed")
        self.assertEqual(len(building_rooms), 1)
        self.assertEqual(len(room_devices), 1)
        self.assertEqual(energy, 1.44) #(60 W / 1000) * 24 h

    def setUpSingleHRManyD(self):
        """Single HR - House, Room; Many Devices"""
        
        user = User.objects.create(id=10, email="defaultuser@email.com", password="defaultpassword")
        building = Building.objects.create(id=10, user=user, name="house2")
        room = Room.objects.create(id=10, building=building, name="kitchen2", area=50)
        device_1 = EnergyReceiver.objects.create(id=10, room=room, name="bulb1", state=False, energy_consumption=50)
        device_2 = EnergyReceiver.objects.create(id=11, room=room, name="bulb2", state=False, energy_consumption=60)
        device_3 = EnergyReceiver.objects.create(id=15, room=room, name="bulb3", state=False, energy_consumption=70)
        energy_receivers = []
        energy_receivers.append(device_1)
        energy_receivers.append(device_2)
        energy_receivers.append(device_3)
        return energy_receivers

    def get_date_from_string(self, date):
        date_format_str = '%Y-%m-%d %H:%M:%S'
        return datetime.strptime(date, date_format_str)

    def test_calculate_singleHR_many_device_energy_consumption_right(self):
        """Energy consumped by many devices in single house is calculated correctly"""
        devices = self.setUpSingleHRManyD()
        turned_on_1 = self.get_date_from_string("2022-03-30 12:00:00")
        turned_off_1 =  self.get_date_from_string("2022-03-30 12:30:00") #diff = 0.5

        turned_on_2 = self.get_date_from_string("2022-03-30 12:00:00")
        turned_off_2 =  self.get_date_from_string("2022-03-30 14:30:00") #diff = 2.5

        turned_on_3 = self.get_date_from_string("2022-03-30 10:00:00")
        turned_off_3 =  self.get_date_from_string("2022-03-30 18:30:00") #diff = 8.5

        DeviceRaport.objects.create(id=10, device=devices[0], turned_on=turned_on_1, turned_off=turned_off_1)
        DeviceRaport.objects.create(id=11, device=devices[1], turned_on=turned_on_2, turned_off=turned_off_2)
        DeviceRaport.objects.create(id=12, device=devices[2], turned_on=turned_on_3, turned_off=turned_off_3) #is this really create object in DB?
        response = self.client.get('/api/buildings/10/energy/', format='json')

        building_rooms = response.data.get("building_rooms", [])
        room_devices = building_rooms[0].get("room_devices",[])
        energy_1 = round(room_devices[0].get("energy_consumed"), 6) #0.025000
        energy_2 = round(room_devices[1].get("energy_consumed"), 6) #0.150000
        energy_3 = round(room_devices[2].get("energy_consumed"), 6) #0.595000
        sum_of_energy = energy_1 + energy_2 + energy_3

        self.assertEqual(len(building_rooms), 1)
        self.assertEqual(len(room_devices), 3)
        self.assertEqual(energy_1, 0.025000) 
        self.assertEqual(energy_2, 0.150000)
        self.assertEqual(energy_3, 0.595000)
        #self.assertEqual(energy_3, 0.595) #be careful because sometimes there is rounding like this (AssertionError: 0.5950000000000001 != 0.595) -> it can be corrected and write tests 
        self.assertEqual(sum_of_energy, 0.77) #0.025 + 0.15 + 0.595 = 0.77
        



