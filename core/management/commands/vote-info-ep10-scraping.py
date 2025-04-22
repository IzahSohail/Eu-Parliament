import os
import csv
import re
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Scrape vote labels from a specific EP10 roll-call page and save to CSV'

    def handle(self, *args, **kwargs):
        url = "https://www.europarl.europa.eu/doceo/document/PV-10-2024-11-14-RCV_EN.html"
        output_csv = "scraped_votes_2024_11_14.csv"

        def humanize_amendment(raw_text):
            if "Commission proposal" in raw_text:
                return "Commission proposal"

            match_am = re.search(r'Am\s?(\d+)', raw_text)
            match_article = re.search(r'Article\s(\d+)', raw_text)
            match_section = re.search(r'\u00a7\s?(\d+)', raw_text) or re.search(r'\u00a7\s?(\d+)', raw_text.replace("§", "\u00a7"))
            match_point = re.search(r'(before|after)\s+point\s+(\d+)', raw_text)
            match_regulation = re.search(r'Regulation \(EU\)\s([\d/]+)', raw_text)

            am = f"Amendment {match_am.group(1)}" if match_am else ""
            article = f"Article {match_article.group(1)}" if match_article else ""
            section = f"Section {match_section.group(1)}" if match_section else ""
            point = f"({match_point.group(1)} point {match_point.group(2)})" if match_point else ""
            regulation = f"of Regulation {match_regulation.group(1)}" if match_regulation else ""

            return " ".join(filter(None, [am, "to", article, section, regulation, point]))

        response = requests.get(url)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch the page: {url}"))
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        vote_blocks = soup.select("table.doc_box_header")

        rows = []
        vote_counter = 1

        for block in vote_blocks:
            try:
                title_container = block.select_one("td.doceo_rcv_title_dossier_1")
                if not title_container:
                    continue
                main_label = title_container.get_text(strip=True).replace("\xa0", " ")
                main_label = re.sub(r'^\d+\.\s*', '', main_label)

                sub_votes = block.select("td.doceo_rcv_title_dossier_2")
                for sub in sub_votes:
                    amendment_raw = sub.get_text(strip=True).replace("\xa0", " ")
                    readable = humanize_amendment(amendment_raw)
                    final_label = f"{main_label} ({readable})"
                    rows.append({"vote_id": vote_counter, "label": final_label})
                    vote_counter += 1
            except Exception as e:
                self.stdout.write(f"Skipping a block due to error: {e}")

        with open(output_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["vote_id", "label"])
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Saved {len(rows)} rows to {output_csv}"))