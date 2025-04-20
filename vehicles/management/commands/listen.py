from django.db import connection
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    def handle(self, *args, **options):
        assert settings.NEW_VEHICLE_WEBHOOK_URL, "NEW_VEHICLE_WEBHOOK_URL is not set"

        session = requests.Session()

        with connection.cursor() as cursor:
            cursor.execute("""CREATE OR REPLACE FUNCTION notify_new_vehicle()
                           RETURNS trigger AS $$
                           BEGIN
                           PERFORM pg_notify('new_vehicle', NEW.slug);
                           RETURN NEW;
                           END;
                           $$ LANGUAGE plpgsql;""")
            cursor.execute("""CREATE OR REPLACE TRIGGER notify_new_vehicle
                           AFTER INSERT ON vehicles_vehicle
                           FOR EACH ROW
                           EXECUTE PROCEDURE notify_new_vehicle();""")

            cursor.execute("LISTEN new_vehicle")
            gen = cursor.connection.notifies()
            NOCs = ["BNML", "BNSM", "BNDB", "BNGN", "BNVB", "BNFM", "ANTR", "SPCT", "HULS"]
            for notify in gen:
                if notify.payload[:4].upper() in NOCs:
                    content = f"BEE NETWORK https://timesbus.org/vehicles/{notify.payload}"
                    allowed_mentions = {"parse": []}
                else:
                    content = f"https://timesbus.org/vehicles/{notify.payload}"
                    allowed_mentions = {"parse": []}  # Prevent accidental pings

                response = session.post(
                    settings.NEW_VEHICLE_WEBHOOK_URL,
                    json={
                        "username": "Velio",
                        "content": content,
                        "allowed_mentions": allowed_mentions,
                    },
                    timeout=5,
                )
                print(response.text)
                time.sleep(2)
