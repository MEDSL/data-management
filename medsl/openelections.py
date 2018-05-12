# coding: utf-8
"""
Provide Open Elections returns for validation. WIP; not yet in use.
"""

import pandas as pd

from medsl.paths import openelections_dir


def read_oe_precincts(path, usecols=['county', 'precinct', 'office', 'district', 'candidate', 'party', 'votes']):
    """Read expected columns from an Open Elections returns CSV."""
    # path = openelections_path() / 'openelections-data-ny/2016/20161108__ny__general__allegany__precinct.csv'
    try:
        df = pd.read_csv(path, usecols=usecols, low_memory=False)
    except ValueError as e:
        print("Error reading {}: {}".format(path, e))
        df = pd.read_csv(path, low_memory=False, thousands=',', dtype={'votes': 'float'})
        missing_cols = set(usecols) - set(df.columns)
        print('Missing columns {}'.format(', '.join(sorted(missing_cols))))
        print('Found columns {}'.format(', '.join(sorted(df.columns))))
        return None
    df['path'] = path.name
    return df


def read_oe_dir(path):
    """Read precinct returns from a directory of Open Elections returns CSVs."""
    csv_paths = path.glob('*precinct.csv')
    df = pd.concat([read_oe_precincts(p) for p in csv_paths])
    df = coerce_vote_type(df)
    df = normalize_candidates(df)
    df = drop_totals(df)
    return df


def coerce_vote_type(df):
    df.votes[df.votes.apply(type) == str] = df.votes[df.votes.apply(type) == str].str.replace(',', '')
    df.votes = df.votes.astype('float')
    return df


def normalize_candidates(df):
    df.candidate = df.candidate.str.lower() \
        .replace(r'\(.*\)', '', regex=True) \
        .replace(r' [a-z]\.* ', ' ', regex=True) \
        .replace(r'([^,]+), ([^,]+)', r'\2 \1', regex=True) \
        .replace(r'\s+', ' ', regex=True) \
        .replace(r'\.$', '', regex=True) \
        .replace(', i', ' i') \
        .replace(r'.*write.*in.*', 'write-in', regex=True) \
        .replace('\s*/\s*', '/', regex=True) \
        .str.strip()
    return df


def drop_totals(df):
    return df.loc[~df.candidate.str.contains('total', case=False, na=False)]


def tally_by_candidate_office(df):
    return df.groupby(['office', 'candidate'], as_index=False).agg({'votes': 'sum'})


if __name__ == '__main__':
    df = read_oe_dir(openelections_dir / 'openelections-data-ny' / '2016')
    tally_by_candidate_office(df)
