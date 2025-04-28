import datetime
import requests
import csv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from core.models import MEP  # Make sure this model is correct

class Command(BaseCommand):
    help = 'Fetch full membership history (all start and end dates) for all MEPs'

    def handle(self, *args, **options):
        start_time = datetime.datetime.now()

        parsed_data = []
        page_with_these_mep_ids_DNE = []
        issue_with_the_page = []

        mep_ids = list(MEP.objects.values_list('mep_id', flat=True))
        print(f"Found {len(mep_ids)} MEPs to scrape.\n")

        def fetch_mep_memberships(mep_id):
            temp_data = []
            today = datetime.date.today()
            ep10_start = datetime.date(2024, 7, 16)

            try:
                source = requests.get(f'https://www.europarl.europa.eu/meps/en/{mep_id}/ANYTHING_GOES/home', timeout=10).text
                soup = BeautifulSoup(source, 'lxml')
                accordion = soup.find('div', class_='erpl_accordion')

                if accordion:
                    mep_home_page = accordion.find_all('ul')[-1].find_all('span')
                    parliamentary_terms = [term.text[0] for term in mep_home_page]
                else:
                    parliamentary_terms = []

                # Add EP10 manually if we're past July 16, 2024
                if today >= ep10_start and '10' not in parliamentary_terms:
                    parliamentary_terms.append('10')

            except Exception as e:
                print(f"[!] Failed to fetch homepage for MEP {mep_id}: {e}")
                page_with_these_mep_ids_DNE.append(mep_id)
                return temp_data

            for parliamentary_term in parliamentary_terms[::-1]:
                try:
                    url = f'https://www.europarl.europa.eu/meps/en/{mep_id}/ANYTHING_GOES/history/{parliamentary_term}#detailedcardmep'
                    source = requests.get(url, timeout=10).text
                    soup = BeautifulSoup(source, 'lxml')
                    political_groups = soup.find('div', class_='erpl_meps-status')

                    if not political_groups:
                        print(f"[!] No political group found for MEP {mep_id} in EP{parliamentary_term}")
                        continue

                    for membership in political_groups.find_all('li'):
                        text = membership.text.strip()

                        if ' / ' in text:
                            start_date = text.split('/')[0].strip()
                            end_date = text.split('/')[1].split(':')[0].strip()
                        else:
                            start_date = text.split('...')[0].strip()
                            end_date = None

                        try:
                            political_group = text.split(':')[1].split(' - ')[0].strip()
                        except IndexError:
                            print(f"[!] Could not parse political group for MEP {mep_id}: {text}")
                            continue

                        temp_data.append({
                            'mep_id': mep_id,
                            'parliamentary_term': parliamentary_term,
                            'start_date': start_date,
                            'end_date': end_date,
                            'political_group': political_group
                        })

                except Exception as e:
                    print(f"[!] Error parsing memberships for MEP {mep_id} in EP{parliamentary_term}: {e}")
                    issue_with_the_page.append(mep_id)

            return temp_data

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_mep_memberships, mep_id): mep_id for mep_id in mep_ids}
            for i, future in enumerate(as_completed(futures), 1):
                mep_id = futures[future]
                try:
                    memberships = future.result()
                    parsed_data.extend(memberships)
                    if i % 50 == 0 or i == len(mep_ids):
                        print(f"✅ Processed {i}/{len(mep_ids)} MEPs...")
                except Exception as e:
                    print(f"[!] Exception for MEP {mep_id}: {e}")

        # Write to CSV
        with open('all_meps_membership_data.csv', 'w', newline='') as csvfile:
            fieldnames = ['mep_id', 'parliamentary_term', 'start_date', 'end_date', 'political_group']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for record in parsed_data:
                writer.writerow(record)

        end_time = datetime.datetime.now()
        print("\n=== DONE ===")
        print(f"Start time: {start_time}")
        print(f"End time: {end_time}")
        print(f"Total membership records saved: {len(parsed_data)}")
        print(f"Pages that did not exist: {len(page_with_these_mep_ids_DNE)}")
        print(f"Pages with parsing issues: {len(issue_with_the_page)}")
