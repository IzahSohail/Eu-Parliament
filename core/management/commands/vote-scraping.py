import os
import csv
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Fetch and export voting data for EP10 to CSV from the European Parliament'

    def handle(self, *args, **kwargs):
        base_url = 'https://www.europarl.europa.eu/plenary/en/ajax/getSessionCalendar.html'
        params = {
            'family': 'PV',
            'termId': '10',
            'source': '',
            'dateRef': '',
            'calendarLanguage': 'en'
        }

        vote_info_rows = []
        vote_mapping_rows = []

        def fetch_calendar_data(term_id):
            params['termId'] = term_id
            response = requests.get(base_url, params=params)
            return response.json() if response.status_code == 200 else None

        def fetch_xml(url):
            response = requests.get(url)
            return response.content if response.status_code == 200 else None

        def humanize_amendment(raw_text):
            if "Commission proposal" in raw_text:
                return "Commission proposal"
            match_am = re.search(r'Am\s?(\d+)', raw_text)
            match_article = re.search(r'Article\s(\d+)', raw_text)
            match_section = re.search(r'\u00a7\s?(\d+)', raw_text)
            match_point = re.search(r'(before|after)\s+point\s+(\d+)', raw_text)
            match_regulation = re.search(r'Regulation \(EU\)\s([\d/]+)', raw_text)
            am = f"Amendment {match_am.group(1)}" if match_am else ""
            article = f"Article {match_article.group(1)}" if match_article else ""
            section = f"Section {match_section.group(1)}" if match_section else ""
            point = f"({match_point.group(1)} point {match_point.group(2)})" if match_point else ""
            regulation = f"of Regulation {match_regulation.group(1)}" if match_regulation else ""
            return " ".join(filter(None, [am, "to", article, section, regulation, point]))

        def fetch_html_labels(vote_date):
            html_url = f"https://www.europarl.europa.eu/doceo/document/PV-10-{vote_date}-RCV_EN.html"
            response = requests.get(html_url)
            if response.status_code != 200:
                return []
            soup = BeautifulSoup(response.text, 'html.parser')
            vote_blocks = soup.select("table.doc_box_header")
            labels = []

            for block in vote_blocks:
                try:
                    title_container = block.select_one("td.doceo_rcv_title_dossier_1")
                    if not title_container:
                        continue
                    main_label = title_container.get_text(strip=True).replace("\xa0", " ")
                    main_label = re.sub(r'^[0-9]+\.\s*', '', main_label)

                    sub_votes = block.select("td.doceo_rcv_title_dossier_2")
                    minutes_link = block.find("a", string=re.compile("Minutes - Item"))
                    minute_url = "https://www.europarl.europa.eu" + minutes_link['href'] if minutes_link else ""

                    code = None
                    if sub_votes:
                        for sub in sub_votes:
                            code_match = re.search(r'(A10-\d{4}/\d{4})', sub.get_text())
                            if code_match:
                                code = code_match.group(1)
                                break
                    if not code:
                        code_match = re.search(r'(C\d{2}-\d{4}/\d{4})', block.text)
                        code = code_match.group(1) if code_match else None

                    committee = None
                    rapporteur = None

                    if minute_url:
                        minute_res = requests.get(minute_url)
                        if minute_res.status_code == 200:
                            minute_soup = BeautifulSoup(minute_res.text, 'html.parser')
                            full_text = minute_soup.get_text()
                            committee_match = re.search(r'Committee on (.*?)\n', full_text)
                            if committee_match:
                                committee = committee_match.group(1).strip()
                            rapporteur_match = re.search(r'Rapporteur: ([^\n\(]+)', full_text)
                            if rapporteur_match:
                                rapporteur = rapporteur_match.group(1).strip()

                    for sub in sub_votes:
                        amendment_raw = sub.get_text(strip=True).replace("\xa0", " ")
                        readable = humanize_amendment(amendment_raw)
                        full_label = f"{main_label} ({readable})"
                        labels.append({
                            "label": full_label,
                            "code": code,
                            "committee": committee,
                            "rapporteur": rapporteur
                        })
                except Exception:
                    continue
            return labels

        def parse_xml(xml_content, vote_date):
            soup = BeautifulSoup(xml_content, 'xml')
            results = soup.find_all('RollCallVote.Result')
            label_data = fetch_html_labels(vote_date)
            label_index = 0

            for result in results:
                vote_id = result['Identifier']
                label_row = label_data[label_index] if label_index < len(label_data) else {}
                label_index += 1

                vote_info_rows.append({
                    'vote_id': vote_id,
                    'date': vote_date,
                    'label': label_row.get('label', ''),
                    'code': label_row.get('code'),
                    'committee_responsible': label_row.get('committee'),
                    'rapporteur': label_row.get('rapporteur')
                })

                def extract_mappings(vote_type_tag, vote_type_label):
                    if vote_type_tag:
                        for group in vote_type_tag.find_all('Result.PoliticalGroup.List'):
                            for member in group.find_all('PoliticalGroup.Member.Name'):
                                mep_id = member.get('PersId')
                                if mep_id:
                                    vote_mapping_rows.append({
                                        'vote_id': vote_id,
                                        'mep_id': mep_id,
                                        'vote_type': vote_type_label
                                    })

                extract_mappings(result.find('Result.For'), 'For')
                extract_mappings(result.find('Result.Against'), 'Against')
                extract_mappings(result.find('Result.Abstention'), 'Abstain')

        calendar_data = fetch_calendar_data('10')

        if calendar_data:
            start_date = datetime.strptime('2024-07-16', '%Y-%m-%d')
            today = datetime.today()
            session_calendar = calendar_data.get('sessionCalendar', [])

            for session in session_calendar:
                date_str = f"{session['year']}-{int(session['month']):02d}-{int(session['day']):02d}"
                session_date = datetime.strptime(date_str, '%Y-%m-%d')
                if start_date <= session_date <= today:
                    xml_url = f"https://www.europarl.europa.eu/doceo/document/PV-10-{date_str}-RCV_EN.xml"
                    print(f"Processing date: {date_str}")
                    xml_content = fetch_xml(xml_url)
                    if xml_content:
                        parse_xml(xml_content, date_str)

        with open('vote_info_ep10.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['vote_id', 'date', 'label', 'code', 'committee_responsible', 'rapporteur'])
            writer.writeheader()
            writer.writerows(vote_info_rows)

        with open('vote_mapping_ep10.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['vote_id', 'mep_id', 'vote_type'])
            writer.writeheader()
            writer.writerows(vote_mapping_rows)

        self.stdout.write(self.style.SUCCESS("CSV export completed: vote_info_ep10.csv and vote_mapping_ep10.csv"))
