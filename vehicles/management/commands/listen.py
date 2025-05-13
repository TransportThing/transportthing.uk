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
            cursor.execute("""
                CREATE OR REPLACE FUNCTION notify_new_vehicle()
                RETURNS trigger AS $$
                BEGIN
                    PERFORM pg_notify('new_vehicle', NEW.slug);
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)
            cursor.execute("""
                CREATE OR REPLACE TRIGGER notify_new_vehicle
                AFTER INSERT ON vehicles_vehicle
                FOR EACH ROW
                EXECUTE PROCEDURE notify_new_vehicle();
            """)

            cursor.execute("LISTEN new_vehicle")
            gen = cursor.connection.notifies()
            Bee_NOCs = [
                "BNML", "BNSM", "BNDB", "BNGN", "BNVB", "BNFM","SPCT", "HULS"
            ]
            NCTR_NOCs = ["NCTR", "TBTN"]
            tfl_nocs = ["TFLO", "LGEN"]
            tfi_nocs = ["ULB", "FY-", "GLE", "MET", "ACAH", "IE-"]

            COLORS = {
                "bee": 0xFFD700,    # Gold
                "nctr": 0x1E90FF,   # Dodger Blue
                "tfl": 0xA020F0,    # Purple
                "tfi": 0x228B22,    # Forest Green
                "default": 0xCCCCCC # Grey
            }

            for notify in gen:
                slug = notify.payload

                # Split slug into NOC and FN
                if '-' in slug:
                    noc, fn = slug.split('-', 1)
                else:
                    noc, fn = slug, ""

                noc_code = noc.upper()
                group = "default"
                role_id = None

                if noc_code in Bee_NOCs:
                    group = "bee"
                    role_id = "1365027753501659157"
                elif noc_code in NCTR_NOCs:
                    group = "nctr"
                    role_id = "1365028004216180786"
                elif noc_code in tfl_nocs:
                    group = "tfl"
                    role_id = "1365031195737329674"
                elif noc_code in tfi_nocs:
                    group = "tfi"
                    role_id = "1367127895696216104"

                vehicle_url = f"https://timesbus.org/vehicles/{slug}"
                content = f"<@&{role_id}>" if role_id else " "
                allowed_mentions = (
                    {"roles": [role_id]} if role_id else {"parse": []}
                )

                embed = {
                    "title": "New Vehicle Added",
                    "description": f"[View Vehicle]({vehicle_url})",
                    "color": COLORS.get(group, COLORS["default"]),
                    "fields": [
                        {
                            "name": "NOC",
                            "value": noc_code,
                            "inline": True
                        },
                        {
                            "name": "FN",
                            "value": fn,
                            "inline": True
                        }
                    ],
                    "thumbnail": {
                        "url": "https://assets.timesbus.org/favicon.svg"
                    },
                    "footer": {
                        "text": "Timesbus Fleet Tracker"
                    }
                }

                response = session.post(
                    "https://discord.com/api/webhooks/1337069419058171995/A044rf3-lHCSxOjdbtZVUShfQ9d1QyuUfB7r978ezcDaat3tIB5b8H2NQdGRVxwyIm5l",
                    json={
                        "username": "Velio",
                        "content": content,
                        "allowed_mentions": allowed_mentions,
                        "embeds": [embed],
                    },
                    timeout=5,
                )
                print(response.text)
                time.sleep(2)
