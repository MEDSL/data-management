#!/usr/bin/env python3
# coding: utf-8
"""
Pre-release checks against precinct returns datasets. WIP.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plac
import yaml

from medsl.docs import write_frequencies
from medsl.metadata import Metadata
from medsl.paths import module_path, state_csv_path


class Expectations(object):
    """Check precinct data against expectations."""

    def __init__(self, year=2016):
        self.races = yaml.load((module_path / 'metadata' / '{}.yaml'.format(year)).read_text())
        self.district_numbers = yaml.load((module_path / 'metadata' / 'districts.yaml').read_text())
        # Doesn't matter which dataverse we specify here; variable metadata is the same across dataverses
        self.meta = Metadata('house')
        self.state_ids = pd.read_csv(module_path / 'gazetteers' / 'states.csv')
        self.county_ids = read_gazetteer('counties')

    def check(self, df, state_postal=''):
        self.columns(df)
        self.values(df)
        self.states(df, state_postal)
        self.counties(df, state_postal)
        self.districts(df, state_postal)
        self.offices(df, state_postal)
        self.candidates(df)
        self.writein(df)
        self.parties(df)
        self.votes(df)

    def columns(self, df):
        """Returns should have expected columns and no others."""
        expected_columns = {v['name'] for v in self.meta.variable_meta}
        expected_columns.add('dataverse')
        missing_columns = expected_columns - set(df.columns.values)
        unexpected_columns = set(df.columns.values) - expected_columns
        self.print_('Missing columns', missing_columns)
        self.print_('Unexpected columns', unexpected_columns)

    def values(self, df):
        """Check for values that often indicate a problem."""
        for col in ['office', 'precinct', 'district', 'candidate']:
            if col in df.columns:
                for pattern in ['total', 'registered', 'cast', 'votes', 'ballot', 'write']:
                    matches = df[col][df[col].str.contains(pattern, case=False).fillna(False)].unique()
                    if matches.any():
                        self.print_('Check {} values'.format(col), matches)
                matches = df[~df['mode'].str.contains('absentee', case=False)]['mode'].str.contains('absentee').unique()
                if matches.any():
                    self.print_('Unexpected {} values where `mode` != `absentee`'.format(col), matches)

    def states(self, df, valid=''):
        """Returns should have only expected state id values."""
        state_ids = self.state_ids
        if valid:
            state_ids = state_ids[state_ids.state_postal == valid]
        try:
            for col in ['state', 'state_postal', 'state_fips', 'state_icpsr']:
                if not np.in1d(df[col], state_ids[col]).all():
                    self.print_('Unexpected {}'.format(col), set(df[col]) - set(state_ids[col]))
        except KeyError as e:
            print(e)

    def counties(self, df, state_postal=''):
        """Returns should have only expected county id values."""
        county_ids = self.county_ids
        if state_postal:
            county_ids = county_ids[county_ids.state_postal == state_postal]
        try:
            unexpected_county_fips = set(df.query('~county_fips.isnull()').county_fips.values.astype(np.float_)) - \
                                     set(county_ids.county_fips.astype(np.float_))
            self.print_('Unexpected county_fips', unexpected_county_fips)
            unexpected_county_names = set(df.query('~county_name.isnull()').county_name.values) - \
                                      set(county_ids.county_name.values)
            self.print_('Unexpected county_name', unexpected_county_names)
            missing_counties = set(county_ids.county_name.values) - set(
                df.query('~county_name.isnull()').county_name.values)
            self.print_('Missing counties', missing_counties)
        except (KeyError, pd.core.computation.ops.UndefinedVariableError) as e:
            logging.error(e)

    def districts(self, df, state_postal):
        """Expect district numbers in a known range as defined in `districts.yaml`, or `statewide`."""
        if state_postal in self.races['US Senate']:
            unexpected_senate = df.query('office == "US Senate" & district != "statewide"')['district'].unique()
            self.print_('Unexpected district for US Senate', unexpected_senate)
        unexpected_president = df.query('office == "US President" & district != "statewide"')['district'].unique()
        self.print_('Unexpected district for US President', unexpected_president)
        for office in self.district_numbers:
            n_seats = self.district_numbers[office][state_postal]
            observed = df.loc[df.office == office].drop_duplicates()
            if n_seats == 1:
                valid_districts = ['0']
            else:
                valid_districts = [str(x) for x in range(1, n_seats + 1)]
            unexpected_districts = observed.loc[~observed.district.isin(valid_districts), ['district']]
            unexpected_districts.drop_duplicates(inplace=True)
            self.print_('Unexpected {} district'.format(office), unexpected_districts.district.astype(str))

    def offices(self, df, state_postal):
        """Expect returns for known races."""
        if 'US President' not in df.office.values:
            self.print_('Missing office', ['US President'])
        missing_offices = [office for office in self.races if state_postal in self.races[office] and
                           office not in df.office.values]
        self.print_('Missing offices', missing_offices)

    def candidates(self, df):
        """`candidate` should only be missing if `writein` is True."""
        if df.candidate[~df.writein].isnull().any():
            print('Null candidates outside of write-ins')

    def writein(self, df):
        """`writein` should only be True or False"""
        if not df.writein.isin([True, False]).all():
            self.print_('writein', np.unique(df.writein.values))

    def parties(self, df):
        """Expect major parties and `democratic` rather than `democrat`."""
        missing_parties = [party for party in ['republican', 'democratic'] if party not in df.party.values]
        self.print_('Missing party', missing_parties)
        if 'democrat' in df.party.values:
            self.print_('Unexpected party', ['democrat'])

    def votes(self, df):
        """Votes should be ints and non-missing."""
        unexpected_votes = df.votes[df.votes.astype(np.float_) % 1 != 0]
        self.print_('Unexpected votes', unexpected_votes)

    def dataverse(self, df):
        """Expect valid `dataverse` values."""
        expected_dataverses = {'president', 'senate', 'house', 'state', 'local', 'all'}
        unexpected_dataverses = df.dataverse[~df.dataverse.isin(expected_dataverses)]
        self.print_('Unexpected dataverse', unexpected_dataverses)

    def print_(self, description, values):
        """Print values, if there are to print."""
        if isinstance(values, np.ndarray) or isinstance(values, pd.Series):
            if values.size:
                lines = '\n  '.join([str(x) for x in sorted(list(values))])
                print('\n{}:\n  {}'.format(description, lines))
        elif values:
            lines = '\n  '.join(sorted([str(x) for x in list(values)]))
            print('\n{}:\n  {}'.format(description, lines))


class Summary(object):
    """Summarize precinct data for manual review."""

    def __init__(self, df):
        self.df = df.copy()
        self.values = self.unique_values()
        self.freqs = write_frequencies(self.df)
        self.totals = self.constituency_totals()

    def __repr__(self):
        values = 'Values:'
        for k, v in self.values.items():
            values += '\n  `{}`: {}'.format(k, '; '.join(v))
        frequencies = ''
        for v in ['mode', 'special', 'writein', 'office', 'dataverse']:
            frequencies += '\n\n`{}` frequencies:\n'.format(v)
            frequencies += self.freqs.loc[self.freqs.variable == v, ['value', 'count']]. \
                to_string(formatters={'count': '{:,.0f}'.format})
        totals = ''
        for k, v in self.totals.items():
            if 'state' in v.columns:
                del v['state']
            totals += '\n\nMEDSL aggregates for {}:\n'.format(k.title())
            totals += v.to_string(float_format='{:,.0f}'.format)
        return '\n'.join([values, frequencies, totals])

    def unique_values(self):
        columns = sorted(
            ['year', 'special', 'mode', 'state_postal', 'stage', 'party', 'writein', 'district', 'dataverse'])
        values = {col: sorted([str(x) for x in self.df[col].unique()]) for col in columns if col in self.df.columns}
        return values

    def constituency_totals(self):
        totals = {
            office: self._compare_aggregates(self.df.query('office == "US {}"'.format(office.title())), office)
            for office in ['president', 'senate', 'house']
        }
        return totals

    @staticmethod
    def _compare_aggregates(precincts, dataverse='house'):
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


@plac.annotations(
    state_postal=('State postal abbreviation', 'positional', None, str),
)
def main(state_postal):
    """Produce validation output.

    The state precinct Makefile calls this function with output piped to `checks.txt` in a state data directory.
    """
    df = pd.read_csv(state_csv_path(state_postal))
    expectations = Expectations()
    expectations.check(df, state_postal)
    print(Summary(df))


if __name__ == '__main__':
    plac.call(main)
