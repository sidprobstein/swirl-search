'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import django
from django.core.exceptions import ObjectDoesNotExist

from sys import path
from os import environ
from .utils import * 

from swirl.utils import swirl_setdir
path.append(swirl_setdir()) # path to settings.py file
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings') 
django.setup()

from swirl.models import Search, Result

import logging as logger

from operator import itemgetter

from django.urls import reverse

#############################################    
#############################################    

def relevancy_mixer(search_id, results_requested, page, explain=True):

    module_name = 'relevancy_mixer'

    if Search.objects.filter(id=search_id).exists():
        search = Search.objects.get(id=search_id)
        results = Result.objects.filter(search_id=search_id)
    else:
        message = f'Error: Search does not exist: {search_id}'
        logger.error(f'{module_name}: {message}')
        mix_wrapper['messages'].append(message)
        return mix_wrapper
    mix_wrapper = create_mix_wrapper(results)
 
    if search.messages:
        for message in search.messages:
            mix_wrapper['messages'].append(message)
    mix_wrapper['info']['search'] = {}
    mix_wrapper['info']['search']['query_string'] = search.query_string
    mix_wrapper['info']['search']['query_string_processed'] = search.query_string_processed
    mix_wrapper['info']['search']['rescore_url'] = f'http://localhost:8000/swirl/search/?rescore={search.id}'
    mix_wrapper['info']['search']['rerun_url'] = f'http://localhost:8000/swirl/search/?rerun={search.id}'

    # join json_results
    all_results = []
    for result in results:
        all_results = all_results + result.json_results
    found = len(all_results)

    # sort the json_results by score
    sorted_results = sorted(sorted(all_results, key=itemgetter('searchprovider_rank')), key=itemgetter('swirl_score'), reverse=True)

    ########################################
    # finalize results
    mix_wrapper['info']['results'] = {}
    mix_wrapper['info']['results']['retrieved_total'] = found
    # set the order in the dict
    mix_wrapper['info']['results']['retrieved'] = 0

    results_needed = int(page) * int(results_requested)

    if len(sorted_results) > results_needed:
        mix_wrapper['info']['results']['next_page'] = f'http://localhost:8000/swirl/results/?search_id={search_id}&result_mixer=relevancy_mixer&page={int(page)+1}'
    else:
        logger.warning(f'{module_name}: results exhausted for search: {search.id}')

    sorted_results = sorted_results[(int(page)-1)*int(results_requested):int(page)*int(results_requested)]

    # number the results
    numbered_results = []
    result_number = (int(page)-1)*int(results_requested) + 1
    for result in sorted_results:
        result['swirl_rank'] = result_number
        if not explain:
            del result['explain']
        numbered_results.append(result)
        result_number = result_number + 1

    if page > 1:
        mix_wrapper['info']['results']['prev_page'] = f'http://localhost:8000/swirl/results/?search_id={search_id}&result_mixer=relevancy_mixer&page={int(page)-1}'

    # redirect(f'/swirl/results?search_id={new_search.id}')

    mix_wrapper['results'] = numbered_results

    mix_wrapper['info']['results']['retrieved'] = len(numbered_results)

    # last message 
    if len(sorted_results) > 2:
        mix_wrapper['messages'].append("Results ordered by: relevancy_mixer")

    return mix_wrapper 

