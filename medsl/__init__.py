#!/usr/bin/env python3
# coding: utf-8
"""
Define module-level constants.
"""

from collections import OrderedDict

import numpy as np

# These are used in filenames and correspond to what follows the underscores in Dataverse aliases (e.g., 'medsl_local')
DATAVERSE_SHORT_NAMES = ['president', 'senate', 'house', 'state', 'local']

# We expect these columns in release-ready precinct-level data for each state (e.g. 'AK/final/2016-ak-precinct.csv').
# Guessing dtypes can fail when CSVS are large (and exceptions rare), so we specify types for each column.
PRECINCT_COLS = OrderedDict({
    # election characteristics
    'year': int,
    'stage': str,
    'special': bool,
    # state
    'state': str,
    'state_postal': str,
    'state_fips': np.int_,
    'state_icpsr': np.int_,
    # county
    'county_name': str,
    # FIPS and ANSI codes should be integers but may be missing, which requires the float type
    'county_fips': np.float_,
    'county_ansi': np.float_,
    'county_lat': np.float_,
    'county_long': np.float_,
    # administrative jurisdictions
    'jurisdiction': str,
    'precinct': str,
    # candidate
    'candidate': str,
    'candidate_last': str,
    'candidate_first': str,
    'candidate_middle': str,
    'candidate_full': str,
    'candidate_suffix': str,
    'candidate_nickname': str,
    'candidate_fec': str,
    'candidate_fec_name': str,
    'candidate_google': str,
    'candidate_govtrack': str,
    'candidate_icpsr': np.float_,
    'candidate_maplight': str,
    'candidate_normalized': str,
    'candidate_opensecrets': str,
    'candidate_wikidata': str,
    'candidate_party': str,
    # election
    'office': str,
    'district': str,
    'writein': bool,
    'party': str,
    'mode': str,
    'votes': np.int_,
    # data management: expected in final CSVs, excluded from release
    'dataverse': str,
})

# TODO: read from yaml
US_SENATE_RACES = ['AK', 'AR', 'CO', 'FL', 'GA', 'IL', 'IN', 'IA', 'KY', 'LA', 'MO', 'NV', 'NH', 'NC', 'OH', 'PA', 'WI']
