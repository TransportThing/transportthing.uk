import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from django.utils.dateparse import parse_datetime

from busstops.models import Operator, Service
from ...models import Vehicle, VehicleJourney, VehicleLocation
from ...models import Vehicle, VehicleJourney, VehicleLocation, DataSource
from ..import_live_vehicles import ImportLiveVehiclesCommand


class Command(ImportLiveVehiclesCommand):
#class Command(BaseCommand):
    help = "Import live vehicle data for Guernsey from remote JSON API"

    API_URL = "https://ticketless-app.api.urbanthings.cloud/api/2/vehiclepositions?maxLatitude=49.515683&maxLongitude=-2.495113&minLatitude=49.434045&minLongitude=-2.660374"  # 👈 Replace with your actual API URL
    headers = {
        "x-api-key": "TIzVfvPTlb5bjo69rsOPbabDVhwwgSiLaV5MCiME",
        "x-ut-app": "travel.ticketless.app.guernsey;platform=web"
    }
    def handle(self, *args, **kwargs):
        source = DataSource.objects.get(name="Guernsey Buses (UrbanThings)")
        try:
            response = requests.get(self.API_URL, timeout=10, headers=self.headers)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            self.stderr.write(f"Failed to fetch data from API: {e}")
            return

        operator = Operator.objects.filter(noc="GUERNSEY").first()
        if not operator:
            self.stderr.write("Operator not found.")
            return

        for item in data.get("items", []):
            vehicle_code = item.get("vehicleRef")
            reported_time = parse_datetime(item.get("reported"))

            if not vehicle_code or not reported_time:
                continue  # skip invalid entries

            # Get or create vehicle
            vehicle, created = Vehicle.objects.get_or_create(
                code=vehicle_code,
                defaults={"operator": operator, "source": source},
            )

            if created:
                self.stdout.write(f"Created new vehicle: {vehicle_code}")

            # Create journey object
            journey_time = parse_datetime(item.get("scheduledTripStartTime"))
            if journey_time:
                journey, _ = VehicleJourney.objects.get_or_create(
                    vehicle=vehicle,
                    datetime=journey_time,
                    defaults={
                        "destination": item.get("destination", ""),
                        "route_name": item.get("routeName", ""),
                        "code": item.get("tripId", ""),
                        "service": Service.objects.filter(
                            current=True,
                            operator=operator,
                            line_name__iexact=item.get("routeName", "")
                        ).first(),
                        "source": source
                    },
                )
        self.stdout.write(f"Updated vehicle {vehicle_code} at {reported_time}")
    def create_vehicle_location(self, item):
        return VehicleLocation(
            latlong=GEOSGeometry(f"POINT({item['position']['longitude']} {item['position']['latitude']})"),
            heading=item["position"]["bearing"] or None,
        )
