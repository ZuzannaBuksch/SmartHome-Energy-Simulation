import argparse
import os
from datetime import datetime, timedelta
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


import django
django.setup()

from file_readers import JsonFileReader
from smarthome.models import Building, Device, DeviceRaport, WeatherRaport
from smarthome.serializers import DeviceRaportListSerializer, WeatherRaportListSerializer
from users.models import User



class DBPopulater:
    _raports_filenames = ["data_json/first_scenario_raports.json"]
    _weather_filename = ["data_json/weather.json"]
    
    def populate_weather_from_file(self):
        generated_raports = []

        for file in self._weather_filename:
            weather_data = JsonFileReader(file).read_file()
            for date, data in weather_data.items():
                start_date = datetime.strptime(date,"%Y-%m-%d %H:%M:%S")
                end_date = start_date+timedelta(minutes=4,seconds=59,microseconds=59)
                solar_radiation = data.get("real", {}).get("solar_radiation")
                generated_raports.append(WeatherRaport(datetime_from=date, datetime_to=end_date, solar_radiation=solar_radiation))
            
        weather_raports = WeatherRaport.objects.bulk_create(generated_raports, ignore_conflicts=True)
        serializer = WeatherRaportListSerializer(instance={"raports":weather_raports})
        return serializer.data

    def populate_raports_from_file(self):
        generated_raports = []
        for file in self._raports_filenames:
            raports_data = JsonFileReader(file).read_file()
            user = User.objects.get(email=raports_data.get("user_email"))
            building = Building.objects.get(name=raports_data.get("building_name"), user=user)

            devices_raports = raports_data.get("devices")
            for device_data in devices_raports:
                device_name = device_data.get("device_name")
                device = Device.objects.get(name=device_name, building=building)
                for raport_data in device_data.get("raports"):
                    if not raport_data.get("turned_off"):
                        raport_data.pop("turned_off")
                    generated_raports.append(DeviceRaport(device=device, **raport_data))

        devices = DeviceRaport.objects.bulk_create(generated_raports, ignore_conflicts=True)
        serializer = DeviceRaportListSerializer(instance={"raports":devices})
        return serializer.data

def get_parser_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raports", action="store_true", default=False)
    parser.add_argument("--weather", action="store_true", default=False)
    return parser.parse_args()
    
def main():
    db_populater = DBPopulater()

    args = get_parser_args()
    print(args)
    if args.raports:
        print("---raports---")
        print(db_populater.populate_raports_from_file())
    if args.weather:
        print("---weather---")
        print(db_populater.populate_weather_from_file())


if __name__ == "__main__":
    main()
