import csv
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
meps_csv = os.path.join(base_dir, 'meps.csv')
new_meps_csv = os.path.join(base_dir, 'new_meps.csv')

# Load existing MEP IDs
with open(meps_csv, 'r') as f:
    existing_ids = {row['mep_id'] for row in csv.DictReader(f)}

# Filter new_meps.csv
filtered_rows = []
with open(new_meps_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['mep_id'] not in existing_ids:
            filtered_rows.append(row)

# Overwrite new_meps.csv with filtered data
with open(new_meps_csv, 'w', newline='') as f:
    if filtered_rows:
        fieldnames = filtered_rows[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)

print(f"Filtered new_meps.csv. Remaining new MEPs: {len(filtered_rows)}")
