#!/usr/bin/env python3
# coding: utf-8
"""
Pre-release checks against precinct returns datasets. WIP.

This is run from the precinct data Makefile, with the output piped to `checks.txt` in the state data directory.

TODO: check districts against apportionment and presence of returns for expected state races.
TODO: log results centrally
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plac
import yaml

from medsl import US_SENATE_RACES
from medsl.docs import write_frequencies
from medsl.metadata import read_dataset_meta, read_variable_meta
from medsl.paths import module_path
from medsl.release import PrecinctData


@plac.annotations(
    state_postal=('State postal abbreviation', 'positional', None, str),
    values=('Show unique values', 'flag', None, bool)
)
def check_final(state_postal='CA', values=False) -> None:
    print('Checking {}...'.format(state_postal))
    precinct_data = PrecinctData([state_postal])
    df = precinct_data.precinct_returns
    dataset_meta = read_dataset_meta('common/precinct.yaml')
    variable_meta = read_variable_meta(dataset_meta)

    report_missing_columns(df, variable_meta)
    report_suspect_values(df)
    report_duplicates(df)
    report_constituency_totals(df)

    if values:
        report_unique_values(df)

    freqs = write_frequencies(df)
    for varname in ['mode', 'special', 'writein', 'office', 'dataverse']:
        print('\n`{}` frequencies:'.format(varname))
        print(
            freqs.loc[freqs.variable == varname, ['value', 'count']].to_string(formatters={'count': '{:,.0f}'.format}))

    check_state(df, valid={state_postal})
    check_county(df)
    check_district(df, state_postal)
    check_office(df, state_postal)
    check_candidate(df)
    check_writein(df)
    check_party(df)
    check_votes(df)
    check_dataverse(df)


def check_dataverse(df):
    dataverses = set({'president', 'senate', 'house', 'state', 'local', 'all'})
    if not df.dataverse.isin(dataverses).all():
        print('\nUnexpected dataverse values: {}'.format('; '.join([str(dv) for dv in set(df.dataverse) - dataverses])))


def report_constituency_totals(df):
    for office in ['president', 'senate', 'house']:
        comparison = compare_aggregates(df.query('office == "US {}"'.format(office.title())), office)
        del comparison['state']
        print('\nMEDSL aggregates for {}:'.format(office.title()))
        print(comparison.to_string(float_format='{:,.0f}'.format))


def compare_aggregates(precincts, dataverse='house'):
    """Compare aggregates of precinct and district returns.
    """
    # Read district/constituency data
    if dataverse == 'house':
        district_dataset = '1976-2016-district-{}'.format(dataverse)
    else:
        district_dataset = '1976-2016-state-{}'.format(dataverse)
    # FIXME: release-ready constituency returns still live in ./output but should be moved into a sibling directory,
    # just as the precinct returns were, like:
    # districts = pd.read_csv(Path(dataset_output_path(Path(district_dataset)) / '{}.csv'.format(district_dataset)))
    districts = pd.read_csv(Path(module_path, 'output', district_dataset, '1976-2016-{}.csv'.format(dataverse)))

    # Keep district data where we have precinct data for comparison
    districts = districts.loc[districts.year == 2016]
    districts = districts.loc[districts.state.isin(set(precincts.state))]
    # Normalize candidate names in district data
    districts = districts.assign(candidate=districts.candidate.str.replace('([^,]+), ([^,]+)', '\\2 \\1'))
    districts = districts.assign(candidate=districts.candidate.str.replace(' [A-Z]\\. ', ' '))
    districts = districts.assign(candidate=districts.candidate.str.replace('Estella ', ''))
    districts = districts.assign(candidate=districts.candidate.str.replace('Roque \"\"Rocky\"\"', 'Rocky'))

    # Tidy up
    keep = ['state', 'candidate', 'party']
    districts.rename({'candidatevotes': 'district_votes'}, axis=1, inplace=True)
    precincts = precincts.copy()
    precincts.rename({'votes': 'precinct_votes'}, axis=1, inplace=True)
    precincts = precincts[keep + ['precinct_votes']]
    districts = districts[keep + ['district_votes']]

    # Aggregate (e.g. over candidates) to district totals
    by = ['state', 'candidate']
    precinct_totals = precincts.groupby(by, as_index=False).agg({'precinct_votes': sum})
    district_totals = districts.groupby(by, as_index=False).agg({'district_votes': sum})
    totals = pd.merge(precinct_totals, district_totals, how='outer')

    # Add final total row and difference column
    total_row = totals.sum(numeric_only=True)
    total_row['candidate'] = 'Total'
    totals = totals.append(total_row, ignore_index=True)
    totals = totals.assign(votes_diff=totals.precinct_votes - totals.district_votes)

    return totals


def check_state(df, valid):
    states = pd.read_csv(module_path / 'gazetteers' / 'states.csv')
    if valid:
        states = states[states.state_postal.isin(valid)]
    try:
        if not np.in1d(df.state, states.state).all():
            print('Unexpected state value: {}'.format(set(df.state) - set(states.state)))
        if not np.in1d(df.state_postal, states.state_postal).all():
            print('Unexpected state_postal value: {}'.format(set(df.state_postal) - set(states.state_postal)))
        if not np.in1d(df.state_fips, states.state_fips).all():
            print('Unexpected state_fips value: {}'.format(set(df.state_fips) - set(states.state_fips)))
        if not np.in1d(df.state_icpsr, states.state_icpsr).all():
            print('Unexpected state_icpsr value: {}'.format(set(df.state_icpsr) - set(states.state_icpsr)))
    except AttributeError as e:
        print(e)


def check_county(df):
    try:
        counties = read_gazetteer('counties')
        unexpected_county_fips = set(df.query('~county_fips.isnull()').county_fips.values.astype(np.float_)) - set(
            counties.GEOID.astype(np.float_))
        unexpected_county_names = set(df.query('~county_name.isnull()').county_name.values) - set(counties.NAME.values)
        missing_counties = set(counties.county_name.values) - set(df.query('~county_name.isnull()').county_name.values)
        if unexpected_county_names:
            print('Unexpected county names: {}'.format(unexpected_county_names))
        if unexpected_county_fips:
            print('Unexpected county FIPS: {}'.format(unexpected_county_fips))
        if missing_counties:
            print('Missing counties: {}'.format(missing_counties))
    except (KeyError, pd.core.computation.ops.UndefinedVariableError) as e:
        logging.error(e)


def check_district(df, state_postal):
    invalid_senate = df.query('office == "US Senate" & district != "statewide"')['district'].unique()
    if invalid_senate.shape[0] and state_postal in US_SENATE_RACES:
        print('Invalid Senate districts: {}'.format(invalid_senate))

    invalid_president = df.query('office == "US President" & district != "statewide"')['district'].unique()
    if invalid_president.shape[0]:
        print('Invalid Senate districts: {}'.format(invalid_president))

    districts = yaml.load(Path(module_path, 'metadata', 'districts.yaml').resolve().read_text())
    for office in districts:
        n_seats = districts[office][state_postal]
        observed = df.loc[df.office == office].drop_duplicates()
        if n_seats == 1:
            valid_districts = ['0']
        else:
            valid_districts = [str(x) for x in range(1, n_seats + 1)]
        invalid = observed.loc[~observed.district.isin(valid_districts), ['district']]
        if invalid.shape[0]:
            print('\nInvalid {} districts:'.format(office))
            print('; '.join(sorted(invalid.drop_duplicates()['district'].astype(str))))

    if any(df.query('office == "State Senate"')['district'].isnull()):
        print('Null district values for State Senate ')

    if any(df.query('office == "State House"')['district'].isnull()):
        print('Null district values for State House ')


def check_office(df, state_postal):
    races = yaml.load(Path(module_path, 'metadata', '2016.yaml').resolve().read_text())
    if 'US President' not in df.office.values:
        print('\nUS President not in `office`')
    for race in races:
        if state_postal in race['states']:
            if race['office'] not in df.office.values:
                print('\nExpected returns for \'{}\', but not found in `office`'.format(race['office']))


def check_candidate(df):
    # Candidate can only be missing for write-ins
    if df.candidate[~df.writein].isnull().any():
        print('Null candidates outside of write-ins')
        print(df.loc[~df.writein & df.candidate.isnull(), ['candidate']].drop_duplicates().to_string())


def check_writein(df):
    if not df.writein.isin([True, False]).all():
        print('Unexpected writein values: {}'.format(np.unique(df.writein.values)))


def check_party(df):
    missing_parties = [party for party in ['republican', 'democratic'] if party not in df.party.values]
    if missing_parties:
        print('Not found in `party`: {}'.format('; '.join(missing_parties)))
    if 'democrat' in df.party.values:
        print('Value `democrat` in `party`')


def check_votes(df):
    # Votes should be ints and non-missing
    if not (df.votes.astype(np.float_) % 1 == 0).all():
        print('Not all votes are non-missing ints')


def report_duplicates(df):
    # Report perfect duplicates
    n = df.shape[0]
    if n:
        duplicates = n - df.drop_duplicates().shape[0]
    else:
        duplicates = 0
    if duplicates:
        print('\n{} duplicate rows'.format(duplicates))


def report_unique_values(df):
    values = {}
    print('\nValues:')
    for col in sorted(['year', 'special', 'mode', 'state', 'stage', 'party', 'writein', 'district', 'dataverse']):
        if col in df.columns:
            values[col] = '; '.join(sorted([str(x) for x in df[col].unique()]))
            print('  `{}`: {}'.format(col, values[col]))
        else:
            values[col] = None


def report_missing_columns(df, variable_meta):
    cols = {v['name'] for v in variable_meta}
    missing_columns = cols - set(df.columns.values)
    extra_columns = set(df.columns.values) - cols
    if missing_columns:
        print('\nMissing expected columns:\n  {}'.format('\n  '.join(sorted(list(missing_columns)))))
    if extra_columns:
        print('\nUnexpected columns:\n  {}'.format('\n  '.join(sorted(list(extra_columns)))))


def report_suspect_values(df):
    exceptions = {}
    for col in ['office', 'precinct', 'district', 'candidate']:
        exceptions[col] = {}
        if col in df.columns:
            for pattern in ['total', 'registered', 'cast', 'votes', 'ballot', 'write']:
                matches = df[col][df[col].str.contains(pattern, case=False).fillna(False)].unique()
                if matches.any():
                    matches = exceptions[col][pattern] = '; '.join(sorted(matches))
                    print('\nFlagged for matching `{}` in `{}`: {}'.format(pattern, col, matches))
            matches = df[~df['mode'].str.contains('absentee', case=False)]['mode'].str.contains('absentee').unique()
            if matches.any():
                print('\nFlagged for matching `absentee` in `{}` where `mode` != `absentee`: {}'.format(
                    col, matches))


def read_gazetteer(unit='counties'):
    if unit == 'counties':
        file = '2017_Gaz_{}_national.txt'.format(unit)
        col_prefix = 'county'
    elif unit == 'cousubs':
        file = '2017_Gaz_{}_national.txt'.format(unit)
        col_prefix = 'county_sub'
    elif unit == 'place':
        file = '2017_Gaz_{}_national.txt'.format(unit)
        col_prefix = unit
    else:
        raise ValueError
    df = pd.read_csv(module_path / 'gazetteers' / file, encoding='latin1', delimiter='\t', dtype=dict(GEOID=str))
    names = {
        'USPS': 'state_postal',
        'GEOID': '{}_fips'.format(col_prefix),
        'NAME': '{}_name'.format(col_prefix)
    }
    df.rename(names, axis=1, inplace=True)
    df = df[list(names.values())]
    return df


if __name__ == '__main__':
    plac.call(check_final)
