import requests
from django.contrib.gis.geos import GEOSGeometry

from busstops.models import Service

from ...models import VehicleJourney, VehicleLocation
from ..import_live_vehicles import ImportLiveVehiclesCommand
from .import_bod_avl import get_line_name_query
from .import_nx import parse_datetime


class Command(ImportLiveVehiclesCommand):
    wait = 92

    def get_items(self):
        self.session = requests.Session()
        return super().get_items()

    @staticmethod
    def add_arguments(parser):
        parser.add_argument("source_name", type=str)
        ImportLiveVehiclesCommand.add_arguments(parser)

    def handle(self, source_name, **options):
        self.source_name = source_name
        super().handle(**options)

    @staticmethod
    def get_datetime(item):
        return parse_datetime(item["RecordedAtTime"])

    def get_vehicle(self, item):
        OPERATOR_REF_MAP = {
            "IRCL": "ie-7778000",
            "HDT": "HRGT",
            "TPEN": "TPEN",
            "BPT": "BPTR",
            "YCD": "YCST",
            "ROS": "ROST",
            "LUI": "LNUD",
            "KDT": "KDTR",
            "NADT": "NADT"
        }
        code = item["VehicleRef"]
        if code.isdigit():
            fleet_number = code
        else:
            fleet_number = None

        if self.source.settings and "OperatorRef" in self.source.settings:
            operators = self.source.settings["OperatorRef"]
            if not isinstance(operators, list):
                operators = [operators]
        else:
            operators = [item["OperatorRef"]]

        # Map operator codes as needed
        operators = [OPERATOR_REF_MAP.get(op, op) for op in operators]
        item["OperatorRef"] = operators  # Update item for downstream use

        defaults = {
            "fleet_number": fleet_number,
            "source": self.source,
            "operator_id": operators[0],
            "code": code,
        }

        try:
            return self.vehicles.get_or_create(
                defaults, code__iexact=code, operator__in=operators
            )
        except self.vehicles.model.MultipleObjectsReturned:
            return (
                self.vehicles.filter(code__iexact=code, operator__in=operators).first(),
                False,
            )

    @classmethod
    def get_service(cls, item):
        line_name = item["PublishedLineName"]
        if not line_name:
            return
        services = Service.objects.filter(
            get_line_name_query(line_name),
            current=True,
            operator__in=item["OperatorRef"],
        )
        try:
            try:
                return services.get()
            except Service.MultipleObjectsReturned:
                return (
                    services.filter(stops__locality__stoppoint=item["DestinationRef"])
                    .distinct()
                    .get()
                )
        except (Service.DoesNotExist, Service.MultipleObjectsReturned) as e:
            print(
                e,
                item["OperatorRef"],
                item["PublishedLineName"],
                item["DestinationRef"],
            )

    def get_journey(self, item, vehicle):
        code = item["JourneyCode"]
        datetime = item["DepartureTime"]
        if datetime:
            datetime = parse_datetime(datetime)
        else:
            datetime = None

        latest_journey = vehicle.latest_journey
        if (
            latest_journey
            and latest_journey.code == code
            and latest_journey.datetime == datetime
        ):
            return latest_journey

        if datetime:
            try:
                return vehicle.vehiclejourney_set.select_related("service").get(
                    datetime=datetime
                )
            except VehicleJourney.DoesNotExist:
                pass

        journey = VehicleJourney(
            datetime=datetime,
            code=code or "",
            route_name=item["PublishedLineName"] or "",
            service=self.get_service(item),
            destination=item["DestinationStopName"] or "",
        )

        if journey.service_id and not journey.id and datetime:
            journey.trip = journey.get_trip(
                departure_time=datetime, destination_ref=item["DestinationRef"]
            )

        return journey

    def create_vehicle_location(self, item):
        bearing = item["Bearing"]
        if bearing == "-1" or bearing == "0":
            bearing = None
        return VehicleLocation(
            latlong=GEOSGeometry(f"POINT({item['Longitude']} {item['Latitude']})"),
            heading=bearing,
        )
