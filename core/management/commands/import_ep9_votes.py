from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import MEP, VoteInfo, VoteMapping
from fuzzywuzzy import process, fuzz
from unidecode import unidecode
import pandas as pd
import csv

# Vote Number Offsets (from original logic)
vote_no_offsets = [0, 0, 886, 3021, 5754, 9494, 15239, 21439, 28402, 38678]

class Command(BaseCommand):
    help = 'Import votes for EP9 from CSV files'

    def handle(self, *args, **options):
        print("Processing EP9 vote data...")

        # Process Vote Info for EP9
        self.process_vote_info_ep9('votes/vote_info_ep9.csv')

        # Process RCV (Roll Call Vote) Mapping for EP9
        self.process_vote_mapping_ep9('votes/rcv_ep9.csv')

        self.stdout.write(self.style.SUCCESS("EP9 data processing complete."))

    def process_vote_info_ep9(self, file_path):
        """Processes vote_info_ep9.csv and extracts relevant fields."""
        print("Processing vote_info_ep9.csv...")

        df = pd.read_csv(file_path, encoding='ISO-8859-1')

        important_columns = {
            'Vote_ID': 'vote_id',
            'Code': 'code',
            'Interinstitutional.file.number': 'interinstitutional_file_no',
            'Title': 'label',
            'Date': 'date',
            'Committee': 'committee_responsible'
        }

        # Keep only important columns and rename them
        df = df[list(important_columns.keys())].rename(columns=important_columns)

        # Convert date format
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

        # Apply vote offset for EP9
        df['vote_id'] = df['vote_id'].str.replace("Vote_", "").astype(int) + vote_no_offsets[9]

        # Save to CSV
        df.to_csv('vote_info_ep9.csv', index=False, encoding='utf-8')
        print("✅ vote_info_ep9.csv created successfully.")

    def find_mep(self, mep_name, term_number=9):
        """Finds the closest matching MEP name from the database for EP9."""
        meps = MEP.objects.filter(
            Q(membership__start_date__lt='2024-07-01') & 
            (Q(membership__end_date__gt='2019-07-01') | Q(membership__end_date__isnull=True))
        ).distinct()

        mep_names = {mep.full_name.lower(): mep.mep_id for mep in meps}
        db_name, match_ratio = process.extractOne(mep_name.lower(), mep_names.keys(), scorer=fuzz.token_sort_ratio)

        return meps.filter(full_name__iexact=db_name).first() if match_ratio > 68 else None

    def process_vote_mapping_ep9(self, file_path):
        """Processes rcv_ep9.csv and maps MEP votes to vote IDs."""
        print("Processing rcv_ep9.csv...")

        df = pd.read_csv(file_path, encoding='ISO-8859-1')
        vote_mappings = []

        # Vote choices mapping
        vote_choices = {1: 'Yes', 2: 'No', 3: 'Abstain'}

        for _, row in df.iterrows():
            mep_name = f"{row['F.Name']} {row['L.Name']}"
            mep = self.find_mep(mep_name)

            if mep:
                for col in df.columns:
                    if col.startswith("Vote_"):  # Ensure it's a vote column
                        try:
                            vote_number = int(col.replace("Vote_", "")) + vote_no_offsets[9]
                            vote_value = row[col]

                            # Handle missing/NA values
                            if pd.isna(vote_value) or vote_value == "NA":
                                vote_type = "Did not vote"
                            else:
                                vote_type = vote_choices.get(vote_value, "Did not vote")

                            vote_mappings.append({
                                "vote_type": vote_type,
                                "mep_id": mep.mep_id,
                                "vote_id": vote_number
                            })

                        except ValueError:
                            print(f"Skipping invalid column: {col}")

        # Save vote mappings to CSV with the correct column order
        with open('vote_mapping_ep9.csv', mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['vote_type', 'mep_id', 'vote_id']  # Correct column order
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vote_mappings)

    print("vote_mapping_ep9.csv written successfully.")
