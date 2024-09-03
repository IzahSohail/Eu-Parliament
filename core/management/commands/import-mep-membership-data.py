from core.models import MEP, PoliticalGroup, Membership
from django.core.management.base import BaseCommand
from django.conf import settings
import datetime
import psycopg2
import csv
import os

class Command(BaseCommand):
    help = 'Imports MEP membership data from a CSV file into the database'

    def handle(self, *args, **options):
        # Define the path to the CSV file relative to the BASE_DIR
        csv_file_path = os.path.join(settings.BASE_DIR, 'all_meps_membership_data.csv')

        try:
            # Open the CSV file and read it row by row
            with open(csv_file_path, 'r') as f:
                reader = csv.DictReader(f)
                unique_groups = set()  # Set to keep track of unique group_id values (useful later)

                # Process each row and save it to the database
                for row in reader:
                    mep_id = row['mep_id']
                    start_date_str = row['start_date']
                    end_date_str = row.get('end_date', '')
                    political_group = row['political_group']

                    # Parse dates in the format DD-MM-YYYY and convert to the appropriate YYYY-MM-DD
                    start_date = datetime.datetime.strptime(start_date_str, '%d-%m-%Y').date()
                    end_date = datetime.datetime.strptime(end_date_str, '%d-%m-%Y').date() if end_date_str else None

                    if political_group not in unique_groups:
                        unique_groups.add(political_group)
                        group = PoliticalGroup(group=political_group)
                        group.save()
                    
                    else:
                        group = PoliticalGroup.objects.get(group=political_group)
                    
                    mep = MEP.objects.get(mep_id=mep_id)
                    membership = Membership(
                        mep=mep,
                        group=group,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    membership.save()

            self.stdout.write(self.style.SUCCESS('Successfully imported CSV data'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing CSV data: {e}'))