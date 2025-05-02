import datetime
from django.contrib.gis.geos import Point
from ..import_live_vehicles import ImportLiveVehiclesCommand
from ...models import VehicleLocation, VehicleJourney
import requests # Make sure to import requests

class Command(ImportLiveVehiclesCommand):
    source_name = "guernsey"
    operator = "TBTEST"
    url = "https://api.timesbus.org/v2/guernsey/vehicles"

    @staticmethod
    def get_datetime(item):
        # The new API provides a datetime string in ISO 8601 format in the 'reported' field
        # Use the 'reported' field for the vehicle location time
        reported_time_str = item.get("reported")
        if reported_time_str:
             # datetime.fromisoformat can handle this
            return datetime.datetime.fromisoformat(reported_time_str.replace('Z', '+00:00'))
        # Fallback to 'received' if 'reported' is not available
        received_time_str = item.get("received")
        if received_time_str:
             # datetime.fromisoformat can handle this
            return datetime.datetime.fromisoformat(received_time_str.replace('Z', '+00:00'))
        return datetime.datetime.now(datetime.timezone.utc) # Fallback to now if neither is available


    def get_vehicle(self, item):
        # The new API has both "vehicleId" (a UUID) and "vehicleRef" (the number)
        # Let's use "vehicleRef" as the code, similar to the original script's logic
        vehicle_code = item.get("vehicleRef")
        if not vehicle_code:
            # Fallback to vehicleId if vehicleRef is missing, though vehicleRef seems more suitable
            vehicle_code = item["vehicleId"]

        defaults = {
            "operator_id": self.operator,
        }
        # We can use vehicleRef as the vehicleRef if it's present and suitable
        if item.get("vehicleRef"):
             defaults["fleet_number"] = item["vehicleRef"]
        # We'll use the vehicleId (UUID) as the source_id for uniqueness from the API
        defaults["source_id"] = item["vehicleRef"]

        # Use vehicle_code for the code field in the get_or_create
        return self.vehicles.get_or_create(
            defaults, source=self.source, code=str(vehicle_code)
        )

    def get_items(self):
        """
        Fetches data from the API, handles the dictionary response structure,
        and returns the list of vehicle items.
        """
        try:
            response = requests.get(self.url)
            response.raise_for_status()  # Raise an exception for bad status codes

            data = response.json()

            # The API returns a dictionary with an "items" key containing the list of vehicles
            vehicle_items = data.get("items", [])
            return vehicle_items

        except requests.exceptions.RequestException as e:
            # Use self.stderr.write for error messages in management commands
            self.stderr.write(self.style.ERROR(f"Error fetching data from API: {e}"))
            return [] # Return an empty list on error
        except ValueError as e:
            # Use self.stderr.write for error messages
            self.stderr.write(self.style.ERROR(f"Error decoding JSON from API: {e}"))
            return [] # Return an empty list on error

    def get_journey(self, item, vehicle):
        # Journey details are now at the top level of the item
        route_name = item.get("routeName")
        direction = item.get("direction")

        if not route_name or not direction:
            return None  # No journey data available

        journey = VehicleJourney()
        journey.route_name = route_name
        # Truncate direction if necessary
        journey.direction = direction[:8]

        # You could also capture routeId, tripId, etc. if needed
        # journey.source_id = item.get("tripId") # Example

        return journey


    def create_vehicle_location(self, item):
        # Position data is nested under a 'position' key
        position_data = item.get("position")
        if not position_data:
            return None # No position data available

        latitude = position_data.get("latitude")
        longitude = position_data.get("longitude")
        bearing = position_data.get("bearing")

        if latitude is None or longitude is None:
             return None # Need valid coordinates

        return VehicleLocation(
            latlong=Point(longitude, latitude), # Corrected order for Point
            heading=bearing, # Use .get() as bearing might be optional
        )

