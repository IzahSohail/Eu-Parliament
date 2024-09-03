from django.shortcuts import render, get_object_or_404
from core.models import MEP, VoteInfo, VoteMapping, Membership
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

    
    
    
    return render(request, 'data_visualization/index.html', {
        'vote_results': vote_results,
        'mep_results': mep_results,
        'query': query,
        'votes_by_date': json.dumps(votes_by_date, cls=DjangoJSONEncoder)
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

    political_groups = defaultdict(list)
    country_votes = defaultdict(list)

    total_yes = 0
    total_no = 0
    total_abstain = 0
    votes_count = vote_mappings.count()

    # Fetch all relevant memberships in one query
    all_memberships = Membership.objects.filter(
        Q(start_date__lte=vote.date) &
        (Q(end_date__gte=vote.date) | Q(end_date__isnull=True))
    ).select_related('group')

    memberships_by_mep = {membership.mep_id: membership for membership in all_memberships}

    for mapping in vote_mappings:
        mep = mapping.mep
        mep_name = f"{mep.first_name} {mep.last_name}"

        # Count votes
        if mapping.vote_type == 'Yes':
            total_yes += 1
        elif mapping.vote_type == 'No':
            total_no += 1
        elif mapping.vote_type == 'Abstain':
            total_abstain += 1

        # Use the pre-fetched membership data
        mep_membership = memberships_by_mep.get(mep.mep_id)
        if mep_membership:
            political_groups[mep_membership.group.group].append({
                'mep_name': mep_name,
                'mep_id': mep.mep_id,
                'vote_type': mapping.vote_type
            })
        else:
            print(f"No membership found for MEP {mep_name} at the time of the vote on {vote.date}")

        # Get MEP's country
        country = mep.country_of_representation
        if country:
            country_votes[country].append({
                'mep_name': mep_name,
                'mep_id': mep.mep_id,
                'vote_type': mapping.vote_type
            })

    # Calculate percentages
    if votes_count > 0:
        percent_yes = (total_yes / votes_count) * 100
        percent_no = (total_no / votes_count) * 100
        percent_abstain = (total_abstain / votes_count) * 100
    else:
        percent_yes = percent_no = percent_abstain = 0

    country_percentages = {}
    for country, votes in country_votes.items():
        total_votes = sum(1 for vote in votes if vote['vote_type'] != 'Present but did not vote')
        yes_votes = sum(1 for vote in votes if vote['vote_type'] == 'Yes')
        in_favor_percentage = (yes_votes / total_votes) * 100 if total_votes > 0 else 0
        country_full_name = get_country_name(country)
        if country_full_name:
            country_percentages[country_full_name] = in_favor_percentage

    group_votes_totaled = []
    for group, votes in political_groups.items():
        group_votes_totaled.append({
            'group': group,
            'total_yes': sum(1 for vote in votes if vote['vote_type'] == 'Yes'),
            'total_no': sum(1 for vote in votes if vote['vote_type'] == 'No'),
            'total_abstain': sum(1 for vote in votes if vote['vote_type'] == 'Abstain')
        })
    group_votes_totaled = sorted(group_votes_totaled, key=lambda x: x['total_yes'], reverse=True)

    country_votes_totaled = []
    for country, votes in country_votes.items():
        country_votes_totaled.append({
            'country': get_country_name(country),
            'total_yes': sum(1 for vote in votes if vote['vote_type'] == 'Yes'),
            'total_no': sum(1 for vote in votes if vote['vote_type'] == 'No'),
            'total_abstain': sum(1 for vote in votes if vote['vote_type'] == 'Abstain')
        })
    country_votes_totaled = sorted(country_votes_totaled, key=lambda x: x['total_yes'], reverse=True)

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
        'political_groups': dict(political_groups),
        'country_votes': dict(country_votes),
        'country_percentages': country_percentages,
        'group_votes_totaled': group_votes_totaled,
        'country_votes_totaled': country_votes_totaled
    })
