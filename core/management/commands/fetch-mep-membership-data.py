from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
import requests
import csv
import datetime

class Command(BaseCommand):
    help = 'Fetches MEP political group data and stores it into a CSV file (only for MEPs in new_meps.csv)'

    def handle(self, *args, **options):
        start_time = datetime.datetime.now()

        # Step 1: Read MEP IDs from new_meps.csv
        mep_ids = []
        with open('new_meps.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                mep_ids.append(row['mep_id'])

        print(f"Total MEPs to process: {len(mep_ids)}")

        parsed_data = []
        page_with_these_mep_ids_DNE = []
        issue_with_the_page = []

        for idx, mep_id in enumerate(mep_ids, 1):
            print(f"[{idx}/{len(mep_ids)}] Fetching data for MEP ID: {mep_id}")

            previous_mep_id, previous_end_date, previous_political_group = "", "", ""

            try:
                source = requests.get(f'https://www.europarl.europa.eu/meps/en/{mep_id}/ANYTHING_GOES/home').text
                soup = BeautifulSoup(source, 'lxml')
                mep_home_page = soup.find('div', class_='erpl_accordion').find_all('ul')[-1].find_all('span')
            except:
                print(f"    [!] MEP ID {mep_id} has no home page.")
                page_with_these_mep_ids_DNE.append(mep_id)
                continue

            try:
                parliamentary_terms = [term.text[0] for term in mep_home_page]

                for parliamentary_term in parliamentary_terms[::-1]:
                    term_url = f'https://www.europarl.europa.eu/meps/en/{mep_id}/ANYTHING_GOES/history/{parliamentary_term}#detailedcardmep'
                    source = requests.get(term_url).text
                    soup = BeautifulSoup(source, 'lxml')
                    political_groups = soup.find('div', class_='erpl_meps-status')

                    for membership in political_groups.find_all('li'):
                        if ' / ' in membership.text:
                            start_date = membership.text.split('/')[0].strip()
                            end_date = membership.text.split('/')[1].split(':')[0].strip()
                        else:
                            start_date = membership.text.split('...')[0].strip()
                            end_date = None

                        political_group = membership.text.split(':')[1].split(' - ')[0].strip()

                        if (
                            political_group == previous_political_group and
                            mep_id == previous_mep_id and
                            previous_end_date and
                            datetime.datetime.strptime(start_date, "%d-%m-%Y") == datetime.datetime.strptime(previous_end_date, "%d-%m-%Y") + datetime.timedelta(days=1)
                        ):
                            parsed_data[-1]["end_date"] = end_date
                        else:
                            parsed_data.append({
                                'mep_id': mep_id,
                                'start_date': start_date,
                                'end_date': end_date,
                                'political_group': political_group
                            })

                        previous_mep_id, previous_end_date, previous_political_group = mep_id, end_date, political_group

            except Exception as e:
                print(f"    [!] Issue fetching/parsing data for MEP ID {mep_id}: {e}")
                issue_with_the_page.append(mep_id)
                continue

        # Save results to CSV
        with open('all_meps_membership_data.csv', 'w', newline='') as csvfile:
            fieldnames = ['mep_id', 'start_date', 'end_date', 'political_group']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(parsed_data)

        end_time = datetime.datetime.now()
        print(f"Start time: {start_time}")
        print(f"End time: {end_time}")
        print(f"Total successful: {len(parsed_data)} entries")
        print(f"Missing home pages: {len(page_with_these_mep_ids_DNE)}")
        print(f"Issues with data: {len(issue_with_the_page)}")
