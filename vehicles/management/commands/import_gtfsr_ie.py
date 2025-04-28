from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.utils.dateparse import parse_duration
from google.protobuf import json_format
from google.transit import gtfs_realtime_pb2

from busstops.models import DataSource, Service
from bustimes.models import Trip
from bustimes.utils import get_calendars

from ...models import Vehicle, VehicleJourney, VehicleLocation
from ..import_live_vehicles import ImportLiveVehiclesCommand


class Command(ImportLiveVehiclesCommand):
    source_name = "Realtime Transport Operators"
    previous_locations = {}

    def do_source(self):
        self.tzinfo = ZoneInfo("Europe/Dublin")
        self.source, _ = DataSource.objects.get_or_create(name=self.source_name)
        self.url = "https://api.nationaltransport.ie/gtfsr/v2/Vehicles"
        return self

    def get_datetime(self, item):
        return datetime.fromtimestamp(item.vehicle.timestamp, timezone.utc)

    def prefetch_vehicles(self, vehicle_codes):
        vehicles = self.vehicles.filter(source=self.source, code__in=vehicle_codes)
        self.vehicle_cache = {vehicle.code: vehicle for vehicle in vehicles}

    def get_items(self):
        assert settings.NTA_API_KEY
        response = self.session.get(
            self.url, headers={"x-api-key": settings.NTA_API_KEY}, timeout=10
        )
        assert response.ok

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        items = []
        vehicle_codes = []

        for item in feed.entity:
            key = item.vehicle.vehicle.id
            value = (
                item.vehicle.trip.route_id,
                item.vehicle.trip.trip_id,
                item.vehicle.trip.start_date,
                item.vehicle.position.latitude,
                item.vehicle.position.longitude,
            )
            if self.previous_locations.get(key) != value:
                items.append(item)
                vehicle_codes.append(key)
                self.previous_locations[key] = value

        self.prefetch_vehicles(vehicle_codes)

        return items

    def get_vehicle(self, item):
        vehicle_code = item.vehicle.vehicle.id

        if vehicle_code in self.vehicle_cache:
            return self.vehicle_cache[vehicle_code], False

        vehicle = Vehicle(
            code=vehicle_code, source=self.source, slug=f"ie-{vehicle_code.lower()}"
        )
        vehicle.save()

        return vehicle, True

    def get_journey(self, item, vehicle):
        start_date = datetime.strptime(
            f"{item.vehicle.trip.start_date} 12:00:00",
            "%Y%m%d %H:%M:%S",
        )
        start_time = parse_duration(item.vehicle.trip.start_time)
        start_date_time = (start_date + start_time - timedelta(hours=12)).replace(
            tzinfo=self.tzinfo
        )

        journey = VehicleJourney(code=item.vehicle.trip.trip_id)

        if (latest_journey := vehicle.latest_journey) and latest_journey.code == journey.code:
            return latest_journey

        journey.datetime = start_date_time

        trip_id = item.vehicle.trip.trip_id
        route_id = item.vehicle.trip.route_id

        service = None

        # Try matching Service where route code is exactly the route_id
        services = Service.objects.filter(
            current=True,
            route__source=self.source,
            route__code=route_id,
        )

        if not services.exists():
            # fallback: match service_code
            services = Service.objects.filter(
                current=True,
                source=self.source,
                service_code__icontains=route_id,
            )

        if services.exists():
            service = services.first()

        trip = None
        trips = Trip.objects.filter(ticket_machine_code=trip_id)

        if service:
            trips = trips.filter(route__service=service)

        if not trips.exists():
            # fallback: try to find trip ignoring service
            trips = Trip.objects.filter(ticket_machine_code=trip_id)

        if trips.exists():
            if trips.count() > 1:
                calendar_ids = [trip.calendar_id for trip in trips]
                calendars = get_calendars(start_date, calendar_ids)
                trips = trips.filter(calendar__in=calendars)
            trip = trips.first()

        # Now link them properly
        if service:
            journey.service = service

        if trip:
            journey.trip = trip
            if not journey.service and trip.route.service:
                journey.service = trip.route.service

            if trip.destination:
                journey.destination = str(trip.destination.locality or trip.destination)
            if trip.operator_id and not vehicle.operator_id:
                vehicle.operator_id = trip.operator_id
                vehicle.save(update_fields=["operator"])

        if journey.service:
            journey.route_name = journey.service.line_name

        vehicle.latest_journey_data = json_format.MessageToDict(item)

        return journey

    def create_vehicle_location(self, item):
        return VehicleLocation(
            heading=item.vehicle.position.bearing or None,
            latlong=GEOSGeometry(
                f"POINT({item.vehicle.position.longitude} {item.vehicle.position.latitude})"
            ),
        )
