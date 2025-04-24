import requests
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from django.utils.dateparse import parse_datetime

from busstops.models import Operator, Service
from ...models import Vehicle, VehicleJourney, VehicleLocation, DataSource
from ..import_live_vehicles import ImportLiveVehiclesCommand

logger = logging.getLogger(__name__)


class Command(ImportLiveVehiclesCommand):
    help = "Import live vehicle data for Guernsey from remote JSON API"

    API_URL = "https://ticketless-app.api.urbanthings.cloud/api/2/vehiclepositions"
    headers = {
        "x-api-key": "",
        "x-ut-app": "",
    }

    def handle(self, *args, **kwargs):
        source = DataSource.objects.get(name="Guernsey Buses (UrbanThings)")
        try:
            response = requests.get(self.API_URL, timeout=10, headers=self.headers)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            self.stderr.write(f"Failed to fetch data from API: {e}")
            logger.error(f"Failed to fetch data from API: {e}")
            return

        operator = Operator.objects.filter(noc="GUERNSEY").first()
        if not operator:
            self.stderr.write("Operator not found.")
            logger.error("Operator not found.")
            return

        for vehicle_data in data.get("items", []):
            vehicle_code = vehicle_data.get("vehicleRef")
            reported_time = parse_datetime(vehicle_data.get("reported"))

            if not vehicle_code or not reported_time:
                logger.warning(
                    f"Skipping entry with missing vehicle_code or reported_time: {vehicle_data}"
                )
                continue

            try:
                vehicle, created = Vehicle.objects.get_or_create(
                    code=vehicle_code,
                    defaults={"operator": operator, "source": source},
                )
            except Vehicle.MultipleObjectsReturned:
                vehicle = Vehicle.objects.filter(code=vehicle_code).first()
                created = False
                logger.warning(
                    f"Multiple vehicles found with code {vehicle_code}. Using the first one."
                )

            if created:
                self.stdout.write(f"Created new vehicle: {vehicle_code}")
                logger.info(f"Created new vehicle: {vehicle_code}")

            journey_time = parse_datetime(vehicle_data.get("scheduledTripStartTime"))
            if journey_time:
                journey, _ = VehicleJourney.objects.get_or_create(
                    vehicle=vehicle,
                    datetime=journey_time,
                    defaults={
                        "destination": vehicle_data.get("destination", ""),
                        "route_name": vehicle_data.get("routeName", ""),
                        "code": vehicle_data.get("tripId", ""),
                        "service": Service.objects.filter(
                            current=True,
                            operator=operator,
                            line_name__iexact=vehicle_data.get("routeName", "")
                        ).first(),
                        "source": source,
                    },
                )

        self.stdout.write(f"Updated vehicle {vehicle_code} at {reported_time}")

    def create_vehicle_location(self, item):
        try:
            longitude = item["position"]["longitude"]
            latitude = item["position"]["latitude"]
            bearing = item["position"].get("bearing")

            if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
                logger.warning(
                    f"Invalid longitude or latitude in vehicle data: {item}"
                )
                return None

        except KeyError as e:
            logger.error(f"Missing 'longitude' or 'latitude' in vehicle data: {item}")
            return None

        return VehicleLocation(
            latlong=GEOSGeometry(f"POINT({longitude} {latitude})"),
            heading=bearing or None,
        )

