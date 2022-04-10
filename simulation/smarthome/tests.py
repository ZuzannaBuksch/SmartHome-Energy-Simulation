from datetime import datetime

from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User

from .models import Building, DeviceRaport, EnergyReceiver, Room


class EnergyTestCase(TestCase):
    client = APIClient()

    def setUpSingleHRD(self):
        """Single HRD - House, Room, Device"""
        user = User.objects.create(id=0, email="usereczek@email.com", password="testusereczek123")
        building = Building.objects.create(id=0, user=user, name="house")
        room = Room.objects.create(id=0, building=building, name="kitchen", area=50)
        return EnergyReceiver.objects.create(id=0, room=room, name="bulb", state=False, energy_consumption=60)
        
    def test_calculate_single_HRD_consumption_right(self):
        """Energy consumped by single device is calculated correctly"""
        device = self.setUpSingleHRD()
        turned_on = self.get_date_from_string("2022-03-30 00:00:00")
        turned_off =  self.get_date_from_string("2022-03-31 00:00:00")
        DeviceRaport.objects.create(id=0, device=device, turned_on=turned_on, turned_off=turned_off)
        response = self.client.get('/api/buildings/0/energy/', format='json')
        building_rooms = response.data.get("building_rooms", [])
        room_devices = building_rooms[0].get("room_devices",[])
        energy = room_devices[0].get("energy_consumed")
        self.assertEqual(len(building_rooms), 1)
        self.assertEqual(len(room_devices), 1)
        self.assertEqual(energy, 1.44)

    def setUpSingleHRManyD(self):
        """Single HR - House, Room; Many Devices"""
        user = User.objects.create(id=10, email="usereczek2@email.com", password="testusereczek123")
        building = Building.objects.create(id=10, user=user, name="house2")
        room = Room.objects.create(id=10, building=building, name="kitchen2", area=50)
        EnergyReceiver.objects.create(id=10, room=room, name="bulb1", state=False, energy_consumption=50)
        EnergyReceiver.objects.create(id=11, room=room, name="bulb2", state=False, energy_consumption=60)
        return EnergyReceiver.objects.create(id=12, room=room, name="bulb3", state=False, energy_consumption=70)

    def get_date_from_string(self, date):
        date_format_str = '%Y-%m-%d %H:%M:%S'
        return datetime.strptime(date, date_format_str)

    def test_calculate_singleHR_many_device_energy_consumption_right(self):
        """Energy consumped by many devices in single house is calculated correctly"""
        device = self.setUpSingleHRManyD()
        turned_on = self.get_date_from_string("2022-03-30 12:00:00")
        turned_off =  self.get_date_from_string("2022-03-30 12:30:00")
        DeviceRaport.objects.create(id=11, device=device, turned_on=turned_on, turned_off=turned_off)
        DeviceRaport.objects.create(id=12, device=device, turned_on=turned_on, turned_off=turned_off)
        response = self.client.get('/api/buildings/10/energy/', format='json')

        building_rooms = response.data.get("building_rooms", [])
        room_devices = building_rooms[0].get("room_devices",[])
        energy = room_devices[0].get("energy_consumed")
        self.assertEqual(len(building_rooms), 1)
        self.assertEqual(len(room_devices), 3)
        self.assertEqual(energy, "not_calculated_yet")



