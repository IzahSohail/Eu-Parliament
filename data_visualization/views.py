from django.shortcuts import render, get_object_or_404
from core.models import MEP, VoteInfo, VoteMapping, Membership, PoliticalGroup
from collections import defaultdict
from io import BytesIO
import base64
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import textwrap
import json
import datetime
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q
import pycountry
from itertools import combinations
import csv


# libraries to install
# numpy, matplotlib, textwrap, pycountry

def wrap_text(text, width):
    return "\n".join(textwrap.wrap(text, width))

def get_country_name(alpha_3_code):
    try:
        return pycountry.countries.get(alpha_3=alpha_3_code).name
    except AttributeError:
        return None

def index(request):
    query = request.GET.get('q')  # gets the query from the search bar
    committee = request.GET.get('committee')  # gets the committee from the URL
    vote_results = None
    mep_results = None

    if query:
        try:
            # to parse the query as a date
            query_date = datetime.datetime.strptime(query, '%Y-%m-%d')
            vote_results = VoteInfo.objects.filter(date=query_date)
        except ValueError:
            # if the query is not a date, search by year or description
            if query.isdigit():
                vote_results = VoteInfo.objects.filter(date__year=query)
            else:
                # check if the query is in the description OR if it is the name of an MEP
                vote_results = VoteInfo.objects.filter(label__icontains=query)
                mep_results = MEP.objects.filter(
                    Q(full_name__icontains=query) |
                    Q(last_name__icontains=query) |
                    Q(first_name__icontains=query)
                ).distinct()
    elif committee:
        # If committee parameter is provided, filter votes by committee_responsible
        vote_results = VoteInfo.objects.filter(committee_responsible__icontains=committee)
    
    # get all vote dates and their votes to highlight in the calendar
    all_votes = VoteInfo.objects.all()
    votes_by_date = {}
    for vote in all_votes:
        date_str = vote.date.strftime('%Y-%m-%d')
        if date_str not in votes_by_date:
            votes_by_date[date_str] = []
        votes_by_date[date_str].append({
            'vote_id': vote.vote_id,
            'label': vote.label
        })

    # to show only the years in the database in the dropdown for the calendar:
    min_vote = all_votes.order_by('date').first()
    max_vote = all_votes.order_by('-date').first()
    min_year = min_vote.date.year if min_vote else 2000
    max_year = max_vote.date.year if max_vote else datetime.datetime.now().year
    
    # Load committees from CSV file
    committees = []
    try:
        with open('../voteview_data/committees.csv', 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row['committee_responsible'] and row['committee_responsible'] not in committees:
                    committees.append(row['committee_responsible'])
        committees.sort()  # Sort alphabetically
    except Exception as e:
        # Handle file not found or other errors
        print(f"Error loading committees: {e}")
    
    return render(request, 'data_visualization/index.html', {
        'vote_results': vote_results,
        'mep_results': mep_results,
        'query': query,
        'committee': committee,  # Pass the selected committee to the template
        'committees': committees,  # Pass the list of committees to the template
        'votes_by_date': json.dumps(votes_by_date, cls=DjangoJSONEncoder),
        'min_year': min_year,
        'max_year': max_year
    })

def mep_info(request, mep_id):
    mep = get_object_or_404(MEP, pk=mep_id)
    photo_data = None
    if mep.photo:
        photo_data = base64.b64encode(mep.photo).decode('utf-8')
        photo_data = f"data:image/png;base64,{photo_data}"

    mep_info = {
        'mep_id': mep.mep_id,
        'name': mep.full_name,
        'country': mep.country_of_representation,
        'photo': photo_data,
        'first_name': mep.first_name,
        'last_name': mep.last_name,
        'gender': mep.gender,
        'date_of_birth': mep.date_of_birth,
        'date_of_death': mep.date_of_death,
        'hometown': mep.hometown,
    }

    return render(request, 'data_visualization/mep_info.html', {
        'mep': mep_info
    })

def get_country_name(alpha_3_code):
    try:
        return pycountry.countries.get(alpha_3=alpha_3_code).name
    except AttributeError:
        return None

def vote_detail(request, vote_id):
    vote = get_object_or_404(VoteInfo, vote_id=vote_id)
    vote_mappings = VoteMapping.objects.filter(vote=vote).select_related('mep')

    # We'll use full group names as keys in this dictionary
    political_groups = defaultdict(list)
    country_votes = defaultdict(list)

    total_yes = total_no = total_abstain = 0
    votes_count = vote_mappings.count()

    all_memberships = Membership.objects.filter(
        Q(start_date__lte=vote.date) &
        (Q(end_date__gte=vote.date) | Q(end_date__isnull=True))
    ).select_related('group')
    memberships_by_mep = {membership.mep_id: membership for membership in all_memberships}

    # Get all political groups
    all_political_groups = PoliticalGroup.objects.all()
    
    # Full name -> shortform mapping
    group_shortform_map = {
        pg.group: pg.shortform if pg.shortform else pg.group
        for pg in all_political_groups
    }
    
    # Shortform -> full name mapping (for the coalition graph legend)
    shortform_group_map = {
        pg.shortform if pg.shortform else pg.group: pg.group
        for pg in all_political_groups
    }

    valid_vote_types = {'Yes', 'No', 'Abstain'}
    
    # Use short forms as keys for vote counts (for coalition graph)
    group_vote_counts = defaultdict(lambda: {'Yes': 0, 'No': 0, 'Abstain': 0, 'Total': 0})
    
    # Create a reverse mapping from short form to full name
    shortform_to_fullname = {v: k for k, v in group_shortform_map.items()}

    for mapping in vote_mappings:
        mep = mapping.mep
        mep_name = f"{mep.first_name} {mep.last_name}"

        if mapping.vote_type == 'Yes':
            total_yes += 1
        elif mapping.vote_type == 'No':
            total_no += 1
        elif mapping.vote_type == 'Abstain':
            total_abstain += 1

        mep_membership = memberships_by_mep.get(mep.mep_id)
        if mep_membership:
            # Get the full group name
            full_group_name = mep_membership.group.group
            # Get the short form
            short_form = group_shortform_map.get(full_group_name, full_group_name)
            
            # Use full group name as key in political_groups
            political_groups[full_group_name].append({
                'mep_name': mep_name,
                'mep_id': mep.mep_id,
                'vote_type': mapping.vote_type
            })

            # Use short form for vote counts (for coalition graph)
            if mapping.vote_type in valid_vote_types:
                group_vote_counts[short_form][mapping.vote_type] += 1
                group_vote_counts[short_form]['Total'] += 1
        else:
            print(f"No membership found for MEP {mep_name} at {vote.date}")

        country = mep.country_of_representation
        if country:
            country_votes[country].append({
                'mep_name': mep_name,
                'mep_id': mep.mep_id,
                'vote_type': mapping.vote_type
            })

    # Create formatted political groups with both full name and short form
    formatted_political_groups = {}
    for full_name, meps in political_groups.items():
        short_form = group_shortform_map.get(full_name, full_name)
        display_name = f"{full_name} - {short_form}"
        formatted_political_groups[display_name] = meps

    # Vote percentages
    percent_yes = (total_yes / votes_count) * 100 if votes_count else 0
    percent_no = (total_no / votes_count) * 100 if votes_count else 0
    percent_abstain = (total_abstain / votes_count) * 100 if votes_count else 0

    country_percentages = {
        get_country_name(country): (
            (sum(1 for v in votes if v['vote_type'] == 'Yes') /
             sum(1 for v in votes if v['vote_type'] != 'Present but did not vote')) * 100
            if sum(1 for v in votes if v['vote_type'] != 'Present but did not vote') > 0 else 0
        )
        for country, votes in country_votes.items()
        if get_country_name(country)
    }

    # Use full group names with short forms for totaled votes
    group_votes_totaled = sorted([
        {
            'group': full_name,
            'display_name': f"{full_name} - {group_shortform_map.get(full_name, full_name)}",
            'total_yes': sum(1 for v in votes if v['vote_type'] == 'Yes'),
            'total_no': sum(1 for v in votes if v['vote_type'] == 'No'),
            'total_abstain': sum(1 for v in votes if v['vote_type'] == 'Abstain')
        } for full_name, votes in political_groups.items()
    ], key=lambda x: x['total_yes'], reverse=True)

    country_votes_totaled = sorted([
        {
            'country': get_country_name(country),
            'total_yes': sum(1 for v in votes if v['vote_type'] == 'Yes'),
            'total_no': sum(1 for v in votes if v['vote_type'] == 'No'),
            'total_abstain': sum(1 for v in votes if v['vote_type'] == 'Abstain')
        } for country, votes in country_votes.items()
    ], key=lambda x: x['total_yes'], reverse=True)

    # ✅ Coalition Matrix - using short forms
    coalition_matrix = defaultdict(dict)
    political_group_list = list(group_vote_counts.keys())
    isolated_groups = set(political_group_list)

    for group1, group2 in combinations(political_group_list, 2):
        total1, total2 = group_vote_counts[group1]['Total'], group_vote_counts[group2]['Total']
        if total1 > 0 and total2 > 0:
            for vote_type in valid_vote_types:
                percent1 = (group_vote_counts[group1][vote_type] / total1) * 100
                percent2 = (group_vote_counts[group2][vote_type] / total2) * 100
                if percent1 >= 50 and percent2 >= 50:
                    coalition_matrix[group1][group2] = 1
                    coalition_matrix[group2][group1] = 1
                    isolated_groups.discard(group1)
                    isolated_groups.discard(group2)
                    break

    for isolated_group in isolated_groups:
        coalition_matrix[isolated_group] = {}

    return render(request, 'data_visualization/vote_detail.html', {
        'vote': vote,
        'vote_date': vote.date,
        'vote_label': vote.label,
        'vote_id': vote.vote_id,
        'total_votes': votes_count,
        'total_yes': total_yes,
        'total_no': total_no,
        'total_abstain': total_abstain,
        'percent_yes': percent_yes,
        'percent_no': percent_no,
        'percent_abstain': percent_abstain,
        'political_groups': formatted_political_groups,  # Use the formatted dictionary
        'country_votes': dict(country_votes),
        'country_percentages': country_percentages,
        'group_votes_totaled': group_votes_totaled,
        'country_votes_totaled': country_votes_totaled,
        'coalition_matrix': json.dumps(coalition_matrix),
        'group_legend': json.dumps(shortform_group_map)  # Maps short forms to full names
    })
