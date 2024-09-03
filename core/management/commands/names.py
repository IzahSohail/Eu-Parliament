from django.core.management.base import BaseCommand
from django.db.models import Q
from core.models import MEP
from fuzzywuzzy import process, fuzz
import pandas as pd
import psycopg2


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

def find_mep(full_name, i):

    mep = MEP.objects.filter(full_name__iexact=full_name)
    if not mep:
        if full_name == "Gisčle CHARZAT":
            mep = MEP.objects.filter(mep_id=1707)
            print(full_name, "|", mep)

        elif full_name == "Mireille C. ELMALAN":
            mep = MEP.objects.filter(mep_id=1125)
            print(full_name, "|", mep)

        elif full_name == "María del Pilar AYUSO GONZÁLEZ":
            mep = MEP.objects.filter(mep_id=4319)
            print(full_name, "|", mep)

        elif full_name == "Toine MANDERS":
            mep = MEP.objects.filter(mep_id=4560)
            print(full_name, "|", mep)

        elif full_name == "Charles TANNOCK":
            mep = MEP.objects.filter(mep_id=4521)
            print(full_name, "|", mep)

        elif full_name == "Marí VALENCIANO MARTÍNEZ-OROZCO":
            mep = MEP.objects.filter(mep_id=4334)
            print(full_name, "|", mep)
        
        elif full_name == "Alexander ALVARO":
            mep = MEP.objects.filter(mep_id=28246)
            print(full_name, "|", mep)
        
        elif full_name == "Iliana Malinova IOTOVA":
            mep = MEP.objects.filter(mep_id=38605)

        elif full_name == "Sidonia Elżbieta JĘDRZEJEWSKA":
            mep = MEP.objects.filter(mep_id=96782)

        elif full_name == "Cornelis de JONG":
            mep = MEP.objects.filter(mep_id=96748)
        
        elif full_name == "Franziska KELLER":
            mep = MEP.objects.filter(mep_id=96734)

        else:
            term_start_date = PARLIAMENTARY_TERMS[i]['start_date']
            term_end_date = PARLIAMENTARY_TERMS[i]['end_date']

            # Filter with an OR condition using Q objects
            meps = MEP.objects.filter(
                Q(membership__start_date__lt=term_end_date) & 
                (Q(membership__end_date__gt=term_start_date) | Q(membership__end_date__isnull=True))
                ).values('mep_id', 'full_name').distinct()

            mep_names = [mep['full_name'].lower() for mep in meps]            
            db_name, match_ratio = process.extractOne(full_name.lower(), mep_names, scorer=fuzz.token_sort_ratio)
            if match_ratio > 68:
                mep_id = meps.get(full_name__iexact=db_name)['mep_id']
                print(full_name, "|", db_name)
                return mep_id

    return mep


class Command(BaseCommand):
    help = 'Not sure yet how to describe this'

    def handle(self, *args, **options):

        for j in range(1, 2):
            # Load the Excel file
            file_path = f'ep{j}.xlsx'

            # Read the Excel file into a DataFrame
            df = pd.read_excel(file_path)

            # Extract the "MEPNAME" column and convert it to a list
            name_list = df['MEPNAME'].tolist()

            fails = []
            for name in name_list:
                parts = name.split()

                # Initialize variables to collect the last name and first name parts
                last_name_parts = []
                first_name_parts = []
                
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

                mep = find_mep(full_name, j)
                if not mep:
                    if first_name == "The Lord":
                        mep = MEP.objects.filter(membership__start_date__lt=PARLIAMENTARY_TERMS[j]['end_date'], membership__end_date__gt=PARLIAMENTARY_TERMS[j]['start_date'], last_name__iexact=last_name).distinct()
                        print(full_name, "|", mep)
                        
                    else:
                        fails.append("First name = " + first_name + ' | Last name = ' + last_name)


        '''
        file_path = 'ep7.xlsx'
        df = pd.read_excel(file_path)

        # Concatenate 'Fname' and 'Lname' columns to create a full name
        name_list = df['Fname'] + ' ' + df['Lname']

        # Convert the concatenated Series to a list
        name_list = name_list.tolist()

        #fails = []
        for name in name_list:
            mep = find_mep(name, 7)
            if not mep:
                fails.append(name)

'''

        print("\nNO MATCH:")
        for i in range(len(fails)):
            print(fails[i])

        print(len(fails))