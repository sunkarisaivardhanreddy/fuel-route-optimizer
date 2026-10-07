import csv
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from routes.models import FuelStation


class Command(BaseCommand):
    help = "Import the assessment fuel-price CSV. Use --geocode to geocode all stations in one Census batch."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--geocode", action="store_true", help="Also submit stations to the Census batch geocoder.")
        parser.add_argument("--keep-existing-coordinates", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            required = {
                "OPIS Truckstop ID", "Truckstop Name", "Address",
                "City", "State", "Rack ID", "Retail Price"
            }
            if not required.issubset(reader.fieldnames or set()):
                raise CommandError(f"CSV must contain columns: {sorted(required)}")

            count = 0
            for row in reader:
                FuelStation.objects.update_or_create(
                    opis_id=int(row["OPIS Truckstop ID"]),
                    defaults={
                        "name": row["Truckstop Name"].strip(),
                        "address": row["Address"].strip(),
                        "city": row["City"].strip(),
                        "state": row["State"].strip().upper(),
                        "rack_id": int(row["Rack ID"]) if row["Rack ID"] else None,
                        "retail_price": row["Retail Price"],
                    },
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {count} fuel stations."))

        if options["geocode"]:
            from .geocode_stations import geocode_all
            geocode_all(self.stdout, keep_existing=options["keep_existing_coordinates"])
