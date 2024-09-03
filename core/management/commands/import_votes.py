from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import MEP, VoteInfo, VoteMapping
from fuzzywuzzy import process, fuzz
from unidecode import unidecode
import pandas as pd
import psycopg2
import csv
from django.db.models import Func


class Unaccent(Func):
    function = 'unaccent'
    template = '%(function)s(%(expressions)s)'


PARLIAMENTARY_TERMS = [
    {}, # offsetting the list by index of 1, so that ep1 corresponds to parliamentary_terms[1], and so on...
    {'start_date': '1979-07-01', 'end_date': '1984-05-31'},
    {'start_date': '1984-07-01', 'end_date': '1989-05-31'},
    {'start_date': '1989-07-01', 'end_date': '1994-05-31'},
    {'start_date': '1994-07-01', 'end_date': '1999-05-31'},
    {'start_date': '1999-07-01', 'end_date': '2004-05-31'},
    {},
    {'start_date': '2009-07-01', 'end_date': '2014-05-31'}
]


def find_mep(mep_name, term_number):

    parts = mep_name.split()
    first_name_parts, last_name_parts = [], []
    
    # Iterate over the parts to classify them into last name and first name
    for i in range(len(parts)):
        if parts[i].isupper():
            last_name_parts.append(parts[i])
        else:
            first_name_parts.append(' '.join(parts[i:]))
            break
    
    # Join the parts to form the full first name and last name
    last_name = ' '.join(last_name_parts)
    first_name = ' '.join(first_name_parts)
    full_name = first_name + ' ' + last_name

    mep = MEP.objects.filter(full_name__iexact=full_name)
    if not mep:

        if full_name == "Gisèle CHARZAT":
            mep = MEP.objects.filter(mep_id=1707)

        elif full_name == "Mireille C. ELMALAN":
            mep = MEP.objects.filter(mep_id=1125)

        elif full_name == "María del Pilar AYUSO GONZÁLEZ":
            mep = MEP.objects.filter(mep_id=4319)

        elif full_name == "Toine MANDERS":
            mep = MEP.objects.filter(mep_id=4560)

        elif full_name == "Charles TANNOCK":
            mep = MEP.objects.filter(mep_id=4521)

        elif full_name == "Marí VALENCIANO MARTÍNEZ-OROZCO":
            mep = MEP.objects.filter(mep_id=4334)
        
        elif full_name == "Alexander ALVARO":
            mep = MEP.objects.filter(mep_id=28246)
        
        elif full_name == "Iliana Malinova IOTOVA":
            mep = MEP.objects.filter(mep_id=38605)

        elif full_name == "Sidonia Elżbieta JĘDRZEJEWSKA":
            mep = MEP.objects.filter(mep_id=96782)

        elif full_name == "Cornelis de JONG":
            mep = MEP.objects.filter(mep_id=96748)
        
        elif full_name == "Franziska KELLER":
            mep = MEP.objects.filter(mep_id=96734)

        else:
            term_start_date = PARLIAMENTARY_TERMS[term_number]['start_date']
            term_end_date = PARLIAMENTARY_TERMS[term_number]['end_date']

            # Filter with an OR condition using Q objects
            meps = MEP.objects.filter(
                Q(membership__start_date__lt=term_end_date) & 
                (Q(membership__end_date__gt=term_start_date) | Q(membership__end_date__isnull=True))
                ).distinct()
            
            
            mep_names = [mep.full_name.lower() for mep in meps]          
            db_name, match_ratio = process.extractOne(full_name.lower(), mep_names, scorer=fuzz.token_sort_ratio)
            if match_ratio > 68:
                mep = meps.filter(full_name__iexact=db_name)
            

                

            if not mep:
                if first_name == "The Lord":
                    mep = MEP.objects.filter(membership__start_date__lt=PARLIAMENTARY_TERMS[term_number]['end_date'], 
                                             membership__end_date__gt=PARLIAMENTARY_TERMS[term_number]['start_date'], 
                                             last_name__iexact=last_name).distinct()   
                # elif full_name == "Albert F.L. PÜRTSEN":
                #     mep = MEP.objects.filter(mep_id=727)               
                else:
                    mep = meps.annotate(
                        unaccented_name=Unaccent('full_name')
                    ).filter(unaccented_name__iexact=unidecode(db_name))
                    if mep.exists():
                        print(f"Unaccented match found for {full_name} with {db_name}")
                    else:
                        print(full_name)

    return mep.first()


class Command(BaseCommand):
    help = 'Import votes from an Excel file'

    def handle(self, *args, **options):
        
        file_path = 'votes/vote_info.xls'
        sheets = ['EP1', 'EP2', 'EP3', 'EP4', 'EP5']
        vote_infos = []
        vote_no_offsets = [0, 0, 886, 3021, 5754, 9494, 15239, 21439, 28402]

        issue_columns = [
            'Issue-Economic=1, Other=0', 
            'Issue-Environment=1, Other=0', 
            'Issue-Social/Employment=1, Other=0',
            'Issue-External Trade/Aid=1, Other=0', 
            'Issue-Agriculture=1, Other=0', 
            'Issue-Inter-Institutional/Reform=1, Other=0',
            'Issue-Internal EP=1, Other=0'
        ]

        issue_mapping = {
            'Issue-Economic=1, Other=0': 'Economic',
            'Issue-Environment=1, Other=0': 'Environment',
            'Issue-Social/Employment=1, Other=0': 'Social/Employment',
            'Issue-External Trade/Aid=1, Other=0': 'External Trade/Aid',
            'Issue-Agriculture=1, Other=0': 'Agriculture',
            'Issue-Inter-Institutional/Reform=1, Other=0': 'Inter-Institutional/Reform',
            'Issue-Internal EP=1, Other=0': 'Internal EP'
        }

        for sheet_name in sheets:
            # Read the Excel sheet into a DataFrame
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            for _, row in df.iterrows():       # Ignore the index by using _
                vote_id = f"{row['Vote No.']}"

                # Handle the date conversion
                date_value = row['Date']
                date = pd.to_datetime(date_value) if not pd.isna(date_value) else None

                rapporteur = row['Rapporteur']
                if pd.isna(rapporteur):
                    rapporteur = None

                caller = row['RCV Sponsor']
                if pd.isna(caller):
                    caller = None

                # NEED a more sophisticated logic for EP4 policy issue, as it is spread accross 7 columns
                if sheet_name == 'EP4':
                    # Iterate over each row and extract the main policy issues
                    issues = []
                    for col in issue_columns:
                        if row[col] == 1:
                            issues.append(issue_mapping[col])
                    main_policy_issue = ", ".join(issues)

                else:
                    main_policy_issue = row['Main Policy Issue']
                    if pd.isna(main_policy_issue):
                        main_policy_issue = None
    
                label = row['Long Description']
                if pd.isna(label) or label == '?':
                    label = None

                vote_infos.append({
                    'vote_id': vote_id,
                    'main_policy_issue': main_policy_issue,
                    'label': label,
                    'date': date,
                    'rapporteur': rapporteur,
                    'caller': caller
                })


        xlsx_files = ['vote_info_ep6.xlsx', 'vote_info_ep7.xlsx', 'vote_info_ep8.xlsx']
        for file in xlsx_files:
            # Read the Excel file
            df = pd.read_excel(f'votes/{file}')
            term_number = int(file[12])

            if file == 'vote_info_ep6.xlsx':

                # Columns to extract and their new names
                important_columns = {
                    'euro_act_id': 'vote_id',
                    'title': 'label',
                    'date': 'date',
                    'raporteur': 'rapporteur',
                    'author_name': 'caller',
                    'committee_code': 'committee_responsible',
                    'main_policy_name': 'main_policy_issue'
                }

            elif file == 'vote_info_ep7.xlsx' or file == 'vote_info_ep8.xlsx':

                important_columns = {
                    'Vote ID': 'vote_id',
                    'Title': 'label',
                    'Date': 'date',
                    'Rapporteur': 'rapporteur',
                    'Code': 'code',
                    'interinstitutional file number': 'interinstitutional_file_no',
                    'Committee responsabile': 'committee_responsible',
                    'De/Policy area': 'main_policy_issue',
                    'Author': 'caller'
                }

            # Filter the DataFrame to include only the important columns and rename them
            filtered_df = df[list(important_columns.keys())].rename(columns=important_columns)

            # Handle the author_name (caller) to be None if it is 0
            filtered_df['caller'] = filtered_df['caller'].apply(lambda x: None if x == 0 or pd.isna(x) else x)
            filtered_df['rapporteur'] = filtered_df['rapporteur'].apply(lambda x: None if x == 0 or pd.isna(x) else x)
            filtered_df['main_policy_issue'] = filtered_df['main_policy_issue'].apply(lambda x: None if pd.isna(x) else x)

            # Offset vote_id by the appropriate number
            filtered_df['vote_id'] = filtered_df['vote_id'] + vote_no_offsets[term_number]

            if term_number == 6:
                committee_code_mapping = {
                    "AFET": "Foreign Affairs",
                    "DEVE": "Development",
                    "INTA": "International Trade",
                    "BUDG": "Budgets",
                    "CONT": "Budgetary Control",
                    "ECON": "Economic and Monetary Affairs",
                    "EMPL": "Employment and Social Affairs",
                    "ENVI": "Environment, Public Health and Food Safety",
                    "CLIM": "Temporary Committee on Climate Change",
                    "ITRE": "Industry, Research and Energy",
                    "IMCO": "Internal Market and Consumer Protection",
                    "TRAN": "Transport and Tourism",
                    "TRANS": "Transport and Tourism",
                    "REGI": "Regional Development",
                    "AGRI": "Agriculture and Rural Development",
                    "PECH": "Fisheries",
                    "PECHE": "Fisheries",
                    "CULT": "Culture and Education",
                    "JURI": "Legal Affairs",
                    "LIBE": "Civil Liberties, Justice and Home Affairs",
                    "LIBE ": "Civil Liberties, Justice and Home Affairs",
                    "AFCO": "Constitutional Affairs",
                    "AFCO ": "Constitutional Affairs",                    
                    "FEMM": "Women's Rights and Gender Equality",
                    "PETI": "Petitions",
                    "Temporary Committee": "Temporary Committee",
                    "Conciliation Committee": "Conciliation Committee",
                    "Conciliation": "Conciliation Committee",
                    "Parliament's delegation to the Conciliation Committee ": "Parliament's delegation to the Conciliation Committee"
                }
                
                filtered_df['committee_responsible'] = filtered_df['committee_responsible'].apply(lambda x: None if x == 0 or pd.isna(x) else committee_code_mapping[x])


            if 'code' in filtered_df.columns:
                filtered_df['code'] = filtered_df['code'].apply(lambda x: None if x == 0 or pd.isna(x) else x)
                filtered_df['interinstitutional_file_no'] = filtered_df['interinstitutional_file_no'].apply(lambda x: None if x == 0 or pd.isna(x) else x)
                filtered_df['committee_responsible'] = filtered_df['committee_responsible'].apply(lambda x: None if x == 0 or pd.isna(x) else x)

            # Convert date using pd.to_datetime with check for NaN values
            filtered_df['date'] = filtered_df['date'].apply(lambda x: pd.to_datetime(x) if not pd.isna(x) else None)

            # Convert each row to a dictionary and append to a list
            data_list = filtered_df.to_dict(orient='records')
            vote_infos = vote_infos + data_list

        # Write the vote info to a CSV file
        with open('vote_info.csv', mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['vote_id', 'code', 'interinstitutional_file_no', 'committee_responsible', 'label', 'main_policy_issue', 'date', 'caller', 'rapporteur']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vote_infos)

        self.stdout.write(self.style.SUCCESS('All vote info data exported to a CSV successfully'))


        ##################################################################################################
        ##################################################################################################


        csv_files = ['rcv_ep1.csv', 'rcv_ep2.csv', 'rcv_ep3.csv', 'rcv_ep4.csv', 'rcv_ep5.csv']
        vote_choices = ['', 'Yes', 'No', 'Abstain', 'Present but did not vote']
        vote_mappings = []

        for file in csv_files:
            term_number = int(file[6])
            file_path = f'votes/{file}'
            df = pd.read_csv(file_path, encoding='ISO-8859-1')

            for _, row in df.iterrows():
                mep = find_mep(row['MEPNAME'], term_number)
                                
                for vote in df.columns[5:]:  # Assuming V1 to Vn are columns 5 onwards
                    vote_number = int(vote[1:]) + vote_no_offsets[term_number]
                    vote_type = row[vote]
                    if vote_type == 0 or vote_type == 5:
                        continue

                    # Add the vote mapping data to the list
                    vote_mappings.append({
                        'vote_id': vote_number,
                        'mep_id': mep.mep_id,
                        'vote_type': vote_choices[vote_type]
                    })


        rcv_files = ['rcv_ep6.xlsx', 'rcv_ep7.xlsx', 'rcv_ep8.xlsx']
        vote_choices = ['', 'Yes', 'No', 'Abstain', '', 'Present but did not vote']

        for file in rcv_files:
            # Read the Excel file
            df = pd.read_excel(f'votes/{file}')
            term_number = int(file[6])
            
            for _, row in df.iterrows():

                if term_number == 7:
                    full_name = row['Lname'] + ' ' + row['Fname']
                    mep = find_mep(full_name, 7)
                    mep_id = mep.mep_id
    
                else:
                    mep_id = int(row['WebisteEpID'])

                if term_number == 6:
                    first_vote_column_number = 10

                elif term_number == 7 or term_number == 8:
                    first_vote_column_number = 9

                for vote in df.columns[first_vote_column_number:]:  # Assuming V1 to Vn are columns, where V1 is the first_vote_col_no-th column
                    vote_number = int(vote) + vote_no_offsets[term_number]
                    vote_type = row[vote]
                    if vote_type == 0 or vote_type == 4 or vote_type == 6:
                        continue

                    # Add the vote mapping data to the list
                    vote_mappings.append({
                        'vote_id': vote_number,
                        'mep_id': mep_id,
                        'vote_type': vote_choices[vote_type]
                    })

        # Write the vote mappings to a CSV file
        with open('vote_mappings.csv', mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['vote_id', 'mep_id', 'vote_type']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vote_mappings)

        self.stdout.write(self.style.SUCCESS('All RCV data imported successfully'))

