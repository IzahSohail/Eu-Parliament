import csv
import os
import requests
from PIL import Image
from io import BytesIO
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch MEP photos for MEPs listed in new_meps.csv and add photo path to the CSV.'

    def handle(self, *args, **options):
        input_csv = 'new_meps.csv'
        temp_csv = 'new_meps_updated.csv'
        save_dir = 'mep_photos'
        base_url = "https://www.europarl.europa.eu/mepphoto/"

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        updated_rows = []
        with open(input_csv, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            fieldnames = reader.fieldnames + ['photo'] if 'photo' not in reader.fieldnames else reader.fieldnames
            
            for row in reader:
                mep_id = row['mep_id'].strip()
                photo_url = f"{base_url}{mep_id}.jpg"
                photo_path = os.path.join(save_dir, f"{mep_id}.jpg")
                
                try:
                    response = requests.get(photo_url)
                    if response.status_code == 200:
                        image = Image.open(BytesIO(response.content))
                        image.save(photo_path)
                        row['photo'] = photo_path
                        print(f"Fetched photo for MEP {mep_id} and saved to {photo_path}")
                    else:
                        row['photo'] = ''
                except Exception as e:
                    self.stdout.write(f"Error fetching photo for MEP {mep_id}: {e}")
                    row['photo'] = ''

                updated_rows.append(row)

        with open(temp_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_rows)

        os.replace(temp_csv, input_csv)
        self.stdout.write("Successfully updated new_meps.csv with photo paths.")
