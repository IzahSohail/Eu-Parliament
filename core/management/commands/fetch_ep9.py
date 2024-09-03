from datetime import datetime
import aiohttp  # for async requests so we can fetch multiple URLs at the same time
import asyncio
import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
from fuzzywuzzy import process, fuzz
from django.db.models import Q
from django.db.models import Func
from django.core.management.base import BaseCommand
from core.models import MEP, PoliticalGroup, VoteInfo, VoteMapping
import csv

multiple_matches = []

class Unaccent(Func):
    function = 'unaccent'
    template = '%(function)s(%(expressions)s)'



#ez_last_name_matches = set()
#full_name_matches = set()
#misses = set()
multiple_matches = []

class Unaccent(Func):
    function = 'unaccent'
    template = '%(function)s(%(expressions)s)'


class Command(BaseCommand):
    help = 'Fetch and store voting data from the European Parliament'

    async def fetch_xml_async(self, session, url):
        async with session.get(url) as response:
            if response.status == 200:
                self.stdout.write(f"Fetched XML data from {url}")
                return await response.text(), url
            else:
                self.stdout.write(f"Failed to fetch XML data from {url}. Status code: {response.status}")
                return None, url

    async def fetch_all_xml(self, urls):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_xml_async(session, url) for url in urls]
            return await asyncio.gather(*tasks)

    def handle(self, *args, **kwargs):
        base_url = 'https://www.europarl.europa.eu/plenary/en/ajax/getSessionCalendar.html'
        params = {
            'family': 'PV',
            'termId': '9',  # term ID for 2019-2024
            'source': '',
            'dateRef': '',
            'calendarLanguage': 'en'
        }

        def fetch_calendar_data(term_id):
            params['termId'] = term_id
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                self.stdout.write(f"Failed to fetch data for term {term_id}. Status code: {response.status}")
                return None

        def parse_xml(xml_content, vote_date):
            soup = BeautifulSoup(xml_content, 'xml')
            results = soup.find_all('RollCallVote.Result')

            vote_info_data = []
            vote_mapping_data = []

            # Preliminary check for missing PersId
            for result in results:
                for group in ['Result.For', 'Result.Against', 'Result.Abstentions', 'Result.Abstention']:
                    political_groups = result.find(group)
                    if political_groups:
                        for political_group in political_groups.find_all('Result.PoliticalGroup.List'):

                            for member in political_group.find_all('Member.Name'):
                                mep_id = member.get('PersId')
                                mep_name = member.text.strip()

                                if not mep_id:
                                    # Filter with an OR condition using Q objects
                                    meps = MEP.objects.filter(
                                        Q(membership__start_date__lt='2024-05-31') & 
                                        (Q(membership__end_date__gt='2019-07-01') | Q(membership__end_date__isnull=True))
                                        ).distinct()
                                    
                                    #removing accents = more ez last name matches. 
                                    mep = meps.annotate(
                                                unaccented_name=Unaccent('last_name')
                                            ).filter(unaccented_name__iexact=unidecode(mep_name))

                                    if not mep:
                                        #see if the issue is that we are given a full name
                                        mep_names = [mep.full_name.lower() for mep in meps]          
                                        db_name, match_ratio = process.extractOne(mep_name.lower(), mep_names, scorer=fuzz.token_sort_ratio)
                                        if match_ratio > 68:
                                            mep = meps.filter(full_name__iexact=db_name)
                                            #full_name_matches.add(f"{mep} with {mep_name}")
                                            
                                        #ok the issue is not that we were given a full name. maybe we are given a hard to match last name:
                                        else:                                            
                                            if mep_name == "Maldeikienė":   #DIFFICULT EXCEPTION. only way is to hard-code it
                                                mep = meps.filter(mep_id=197835)
                                            
                                            elif mep_name == "Benjumea":
                                                mep = meps.filter(mep_id=197679)

                                            elif mep_name == "Figueiredo Nobre De Gusmão":
                                                mep = meps.filter(mep_id=88715)

                                            elif mep_name == "Leitão Marques":
                                                mep = meps.filter(mep_id=197635)

                                            elif mep_name == "Tomaševski":
                                                mep = meps.filter(mep_id=96697)
                                            
                                            elif mep_name == "Kopc ińska":
                                                mep = meps.filter(mep_id=197530)

                                            #else:
                                                #misses.add((f"{mep} with {mep_name}"))

                                    else:   #if we were able to get an mep just from the last name, we are good. 
                                        if len(mep) > 1: #just deal with multiple matches! (will do that based on political party / date)

                                            if mep_name == 'Santos':
                                                if political_group['Identifier'] == 'S&D':
                                                    mep = meps.filter(mep_id=197650)
                                                elif political_group['Identifier'] == 'PPE':
                                                    mep = meps.filter(mep_id=254722)
                                                else:
                                                    print("you got an issue with Santos here !!!")
    
                                            elif mep_name == 'Geuking':
                                                if datetime.strptime(vote_date, "%Y-%m-%d").date() > datetime.strptime("2024-02-04", "%Y-%m-%d").date(): #Two guys with the same name are in the same political group. Only difference, one is an MEP until 04-02-2024, and the other is an mep FROM 05-02-2024...
                                                    mep = meps.filter(mep_id=251874)
                                                else:
                                                    mep = meps.filter(mep_id=197436)
                                           
                                            elif mep_name == 'Anderson':
                                                if political_group['Identifier'] == 'ID' or political_group['Identifier'] == 'NI': 
                                                    mep = meps.filter(mep_id=197475) #Christine
                                                elif political_group['Identifier'] == 'GUE/NGL': 
                                                    mep = meps.filter(mep_id=113959) #Martina 
                                                elif political_group['Identifier'] == 'Verts/ALE':
                                                    mep = meps.filter(mep_id=204371) #Heather

                                            else:
                                                multiple_matches.append(mep)

                                        else:
                                            mep_instance = mep.first()  # Get the instance so i can easily access its unaccented name
                                            #ez_last_name_matches.add(f"{mep_instance.unaccented_name} with {mep_name}")



            vote_mappings = []
            mep_cache = {mep.mep_id: mep for mep in MEP.objects.all()}

            for result in results:
                vote_id = result['Identifier']
                vote_title = result.find('RollCallVote.Description.Text').text.strip()

                # delete existing VoteMapping records for this vote_id (adding this while testing code)
                VoteMapping.objects.filter(vote__vote_id=vote_id).delete()

                # NEED TO MAKE A DICTIONARY HERE INSETAD OF CREATING OBJECTS ON THE FLY. SO THAT WE CAN MAKE A CSV FILE LATER
                #update or create vote info
                vote_info, created = VoteInfo.objects.update_or_create(
                    vote_id=vote_id,
                    defaults={
                        'date': vote_date,
                        'label': vote_title,
                    }
                )

                def process_group(vote_type, group):
                    for political_group in group.find_all('Result.PoliticalGroup.List'):
                        for member in political_group.find_all('PoliticalGroup.Member.Name'):
                            mep_id = member.get('PersId')
                            mep_name = member.text.strip()

                            # Skip if MEP ID is 'UNKNOWN'
                            if mep_id == 'UNKNOWN':
                                print(f"Warning: Missing PersId for {mep_name} on date {vote_date}")
                                continue

                            # Fetch the MEP object from cache
                            mep = mep_cache.get(mep_id)

                            if mep:
                                # NEED TO MAKE A DICTIONARY HERE INSETAD OF CREATING OBJECTS ON THE FLY. SO THAT WE CAN MAKE A CSV FILE LATER
                                vote_mappings.append(VoteMapping(
                                    vote=vote_info[0],
                                    mep=mep,
                                    vote_type=vote_type
                                ))
                    return True

                for_group = result.find('Result.For')
                if for_group:
                    process_group('Yes', for_group)

                against_group = result.find('Result.Against')
                if against_group:
                    process_group('No', against_group)

                abstentions_group = result.find('Result.Abstentions') or result.find('Result.Abstention')
                if abstentions_group:
                    process_group('Abstain', abstentions_group)

            # NEED TO MAKE A DICTIONARY HERE INSETAD OF CREATING OBJECTS ON THE FLY. SO THAT WE CAN MAKE A CSV FILE LATER
            #Bulk create VoteMapping instances
            VoteMapping.objects.bulk_create(vote_mappings)

            return


        term_id = '9'
        
        '''
        url = "https://www.europarl.europa.eu/doceo/document/PV-9-2020-07-08-RCV_EN.xml"
        date_str = "2020-07-08"

        # Fetch the XML content for the specific date
        loop = asyncio.get_event_loop()
        xml_results = loop.run_until_complete(self.fetch_all_xml([url]))

        # Process the XML content if it was successfully fetched
        for xml_content, url in xml_results:
            if xml_content:
                parse_xml(xml_content, date_str)
                print(f"Processed vote data for {date_str}")

        '''

        calendar_data = fetch_calendar_data(term_id)

        if calendar_data:
            start_date = datetime.strptime(calendar_data['startDate'], '%d/%m/%Y')
            end_date = datetime.strptime(calendar_data['endDate'], '%d/%m/%Y')

            # checking to see if start and end dates are correct (comment out later)
            # print(f"Start Date: {start_date}, End Date: {end_date}")

            session_calendar = calendar_data.get('sessionCalendar', [])
            urls = []
            date_str_map = {}  # map URLs to their date strings

            for session in session_calendar:
                date_str = f"{session['year']}-{int(session['month']):02d}-{int(session['day']):02d}"
                session_date = datetime.strptime(date_str, '%Y-%m-%d')

                if session['year']=='2019':
                    url = f"https://www.europarl.europa.eu/doceo/document/PV-9-{date_str}-RCV_EN.xml"
                    urls.append(url)
                    date_str_map[url] = date_str

            # print(f"Total URLs to fetch: {len(urls)}")

            loop = asyncio.get_event_loop()
            xml_results = loop.run_until_complete(self.fetch_all_xml(urls))

            # filter out None responses and retain corresponding session dates
            valid_xml_contents = []
            valid_dates = []

            for xml_content, url in xml_results:
                if xml_content:
                    valid_xml_contents.append(xml_content)
                    valid_dates.append(date_str_map[url])

            # verify the lengths of valid_xml_contents and valid_dates (comment out later)
            # print(f"Total valid XML contents: {len(valid_xml_contents)}")
            # print(f"Total valid dates: {len(valid_dates)}")

            all_vote_info_data = []
            all_vote_mapping_data = []

            for xml_content, date_str in zip(valid_xml_contents, valid_dates):
                vote_info_data, vote_mapping_data = parse_xml(xml_content, date_str)
                all_vote_info_data.extend(vote_info_data)
                all_vote_mapping_data.extend(vote_mapping_data)
                # print(f"Processed vote data for {date_str}")

            print("\nMultiple matches: ")
            for match in multiple_matches:
                print(match)

            #print("\nFull Name matches: ")
            #for match in full_name_matches:
            #    print(match)

            #print("\nMisses: ")
            #for miss in misses:
            #    print(miss)

            #print(f"\nEz last name matches: {len(ez_last_name_matches)}")
            #print(f"Full name matches: {len(full_name_matches)}")
            print(f"Multiple matches: {len(multiple_matches)}")
            #print(f"Misses: {len(misses)}\n")

            self.stdout.write(self.style.SUCCESS("Vote data saved"))
#'''