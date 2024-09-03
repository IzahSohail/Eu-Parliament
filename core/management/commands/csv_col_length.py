import csv
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Analyzes a CSV's file column lengths."

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file to be analyzed')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        max_lengths = self.analyze_csv(csv_file)
        
        # Output maximum sizes for each column
        for column, length in max_lengths.items():
            self.stdout.write(f"Maximum size for column '{column}': {length}")

    def analyze_csv(self, csv_file):
        max_lengths = {}
        
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            
            # because the first row contains column headers
            headers = next(reader)
            
            # Initialize max_lengths dictionary with column headers
            for header in headers:
                max_lengths[header] = 0
            
            # Analyze data in each column
            for row in reader:
                for i, value in enumerate(row):
                    column_name = headers[i]
                    max_lengths[column_name] = max(max_lengths[column_name], len(value))
        
        return max_lengths