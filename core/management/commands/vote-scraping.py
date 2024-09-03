import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from core.models import VoteInfo, VoteMapping, MEP, PoliticalGroup

class Command(BaseCommand):
    help = 'Fetch and store voting data from the European Parliament'

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
                self.stdout.write(f"Failed to fetch data for term {term_id}. Status code: {response.status_code}")
                return None

        def fetch_xml(url):
            response = requests.get(url)
            if response.status_code == 200:
                self.stdout.write(f"Fetched XML from {url}")
                return response.content
            else:
                self.stdout.write(f"Failed to fetch XML from {url}. Status code: {response.status_code}")
                return None

        def parse_xml(xml_content, vote_date):
            soup = BeautifulSoup(xml_content, 'xml')
            votes_data = []

            results = soup.find_all('RollCallVote.Result')

            for result in results:
                vote_id = result['Identifier']
                vote_title = result.find('RollCallVote.Description.Text').text.strip()
                #create vote info records
                VoteInfo.objects.get_or_create(
                    vote_id=vote_id,
                    defaults={'label': vote_title, 'date': vote_date}
                )

                for_group = result.find('Result.For')
               
                if for_group:
                    for political_group in for_group.find_all('Result.PoliticalGroup.List'):
                        for group in political_group.find_all('Member.Name'):
                            mep_id = group['MepId']
                            mep_name = group.text.strip()

                            # Ensure MEP exists or create it
                            mep, _ = MEP.objects.get_or_create(
                                mep_id=mep_id,
                                defaults={'full_name': mep_name}
                            )

                            # Create VoteMapping entry
                            VoteMapping.objects.create(
                                vote=VoteInfo.objects.get(vote_id=vote_id),
                                mep=mep,
                                vote_type='For'
                            )
                against_group = result.find('Result.Against')
                if against_group:
                    for political_group in against_group.find_all('Result.PoliticalGroup.List'):
                        for group in political_group.find_all('Member.Name'):
                            mep_id = group['MepId']
                            mep_name = group.text.strip()

                            # Ensure MEP exists or create it
                            mep, _ = MEP.objects.get_or_create(
                                mep_id=mep_id,
                                defaults={'full_name': mep_name}
                            )

                            # Create VoteMapping entry
                            VoteMapping.objects.create(
                                vote=VoteInfo.objects.get(vote_id=vote_id),
                                mep=mep,
                                vote_type='Against'
                            )

                abstentions_group = result.find('Result.Abstention')
                if abstentions_group:
                    for political_group in abstentions_group.find_all('Result.PoliticalGroup.List'):
                        for group in political_group.find_all('Member.Name'):
                            mep_id = group['MepId']
                            mep_name = group.text.strip()

                            # Ensure MEP exists or create it
                            mep, _ = MEP.objects.get_or_create(
                                mep_id=mep_id,
                                defaults={'full_name': mep_name}
                            )

                            # Create VoteMapping entry
                            VoteMapping.objects.create(
                                vote=VoteInfo.objects.get(vote_id=vote_id),
                                mep=mep,
                                vote_type='Abstain'
                            )
                        
                        
                        
                        

                        # # Ensure MEP exists or create it
                        # mep, _ = MEP.objects.get_or_create(
                        #     mep_id=mep_id,
                        #     defaults={'full_name': mep_name}
                        # )

                        # # Create VoteMapping entry
                        # VoteMapping.objects.create(
                        #     vote=vote_id,
                        #     mep=mep,
                        #     vote_type='For'
                        # )

                # against_group = result.find('Result.Against')
                # if against_group:
                #     process_votes(against_group, vote_id, vote_title, vote_date, 'Against', votes_data)

                # abstentions_group = result.find('Result.Abstentions')
                # if abstentions_group:
                #     process_votes(abstentions_group, vote_id, vote_title, vote_date, 'Abstentions', votes_data)

            return votes_data

        # def process_votes(group, vote_id, vote_title, vote_date, vote_type, votes_data):
        #     for political_group in group.find_all('Result.PoliticalGroup.List'):
                
        #         group_id = political_group['Identifier']
        #         for member in political_group.find_all('PoliticalGroup.Member.Name'):
        #             mep_id = member['MepId']
        #             mep_name = member.text.strip()
        #             votes_data.append({
        #                 'date': vote_date,
        #                 'vote_id': vote_id,
        #                 'vote_title': vote_title,
        #                 'vote_type': vote_type,
        #                 'mep_id': mep_id,
        #                 'mep_name': mep_name,
        #                 'group_id': group_id
        #             })

        # def save_to_database(votes_data):
        #     meps = {}
        #     groups = {}
        #     vote_infos = {}
        #     vote_mappings = []

        #     for vote in votes_data:
        #         mep, _ = MEP.objects.get_or_create(
        #             mep_id=vote['mep_id'],
        #             defaults={'full_name': vote['mep_name']}
        #         )
        #         meps[vote['mep_id']] = mep

        #         group, _ = PoliticalGroup.objects.get_or_create(
        #             group=vote['group_id']
        #         )
        #         groups[vote['group_id']] = group

        #         vote_info, _ = VoteInfo.objects.get_or_create(
        #             vote_id=vote['vote_id'],
        #             defaults={
        #                 'label': vote['vote_title'],
        #                 'date': vote['date']
        #             }
        #         )
        #         vote_infos[vote['vote_id']] = vote_info

        #         vote_mappings.append(VoteMapping(
        #             vote=vote_info,
        #             mep=mep,
        #             vote_type=vote['vote_type']
        #         ))

        #     VoteMapping.objects.bulk_create(vote_mappings, ignore_conflicts=True)

        term_id = '9'
        calendar_data = fetch_calendar_data(term_id)

        if calendar_data:
            start_date = datetime.strptime(calendar_data['startDate'], '%d/%m/%Y')
            end_date = datetime.strptime(calendar_data['endDate'], '%d/%m/%Y')

            session_calendar = calendar_data.get('sessionCalendar', [])
            for session in session_calendar:
                date_str = f"{session['year']}-{int(session['month']):02d}-{int(session['day']):02d}"
                session_date = datetime.strptime(date_str, '%Y-%m-%d')

                # for testing purposes, only get data from july - december 2019
                if start_date.year < session_date.year or (start_date.year == session_date.year and session_date.month >= 7 and session_date.month <= 12):
                    url = f"https://www.europarl.europa.eu/doceo/document/PV-9-{date_str}-RCV_EN.xml"
                    xml_content = fetch_xml(url)
                    if xml_content:
                        parse_xml(xml_content, date_str)
                        print(f"Data saved for {date_str}")
                        # Ensure it is actually saved to the database
                        saved_count = VoteInfo.objects.filter(date=date_str).count()
                        vote_mapping = VoteMapping.objects.filter(vote__date=date_str).count()


                        print(f"Records saved for {date_str}: {saved_count}")
                        print(f"Vote Mapping saved for {date_str}: {vote_mapping}")
                        # votes = parse_xml(xml_content, date_str)
                        # if votes:
                        #     save_to_database(votes)
                        #     print(f"Data saved for {date_str}")
                        #     # Ensure it is actually saved to the database
                        #     saved_count = VoteMapping.objects.filter(vote__date=date_str).count()
                        #     print(f"Records saved for {date_str}: {saved_count}")
                        # else:
                        #     print(f"No votes parsed for {date_str}")

            self.stdout.write(self.style.SUCCESS("Vote data has been saved to the database"))
