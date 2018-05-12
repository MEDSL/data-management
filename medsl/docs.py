#!/usr/bin/env python3
# coding: utf-8
"""
Write dataset documentation: codebooks, release notes, and R help.

The approach is to fill Jinja templates using values from YAML files that describe dataset, dataverse, and variable
metadata (see './metadata').

Can be run as a script, but also used by release.py.
"""
import datetime
import logging
import re
from pathlib import Path

import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader

from medsl import DATAVERSE_SHORT_NAMES
from medsl.metadata import read_dataset_meta, read_variable_meta, read_dataverse_meta
from medsl.paths import dataset_output_path, module_path, r_output_path, dataset_meta_yaml_path, \
    precinct_returns_path


class Documentation(object):
    """A class for dataset documentation.
    """

    def __init__(self):
        template_loader = FileSystemLoader(searchpath=str(module_path / 'templates'))
        self.env = Environment(loader=template_loader)
        # The Rd template avoids using braces as delimiters
        self.rd_env = Environment(loader=template_loader, block_start_string='<+', block_end_string='+>',
                                  variable_start_string='<<', variable_end_string='>>', comment_start_string='<#',
                                  comment_end_string='>#')
        # Add custom filters
        self.rd_env.filters['r_alias'] = r_alias
        self.rd_env.filters['format_code'] = format_code
        self.codebook_template = self.env.get_template('codebook.jinja')
        self.notes_template = self.env.get_template('release_notes.jinja')
        self.coverage_template = self.env.get_template('coverage_notes.jinja')
        self.rdata_template = self.rd_env.get_template('r_doc.jinja')

    def write(self, dataverse: str) -> None:
        """Write documentation to disk.

        Writes dataset codebook, release notes, and R documentation to dataset_output_path().

        :param dataverse: The short name for a dataverse: 'president', 'senate', 'house', 'state', or 'local'.
        """
        # Load metadata for the dataset the codebook describes
        dataset_yaml = Path('2016-precinct-{}.yaml'.format(dataverse))
        dataset_meta = read_dataset_meta(dataset_yaml, quietly=True)
        # Use today's date for version id
        dataset_meta['version'] = str(datetime.datetime.today().date())

        # Load metadata for the dataverse of the dataset
        dataverse_meta = read_dataverse_meta(dataset_meta['dataverse'])
        logging.debug('Read dataverse metadata: {}'.format(dataset_meta['dataverse']))

        # Load metadata for the variables in the dataset
        variable_meta = read_variable_meta(dataset_meta, quietly=True)
        del dataset_meta['variables']

        # Populate templates
        codebook = self.codebook_template.render(dataset=dataset_meta, dataverse=dataverse_meta,
                                                 variables=variable_meta)
        notes = self.notes_template.render(dataset=dataset_meta)
        rdata_rd = self.rdata_template.render(dataset=dataset_meta, dataverse=dataverse_meta, variables=variable_meta)
        coverage = self.coverage_template.render(dataset=dataset_meta, states=dataset_meta['coverage'])

        # Destination directory is the name of the dataset YAML, less the .yaml extension,
        # e.g. '2016-precinct-president', under the path returned by dataset_output_path().
        output_dir = dataset_output_path(dataset_yaml)
        r_package_dir = r_output_path()

        # Write documentation to disk
        dataset_name = Path(dataset_yaml).stem
        (output_dir / 'codebook-{}.md'.format(dataset_name)).write_text(codebook)
        (output_dir / 'release-notes-{}.md'.format(dataset_name)).write_text(notes)
        (output_dir / 'coverage-notes-{}.md'.format(dataset_name)).write_text(coverage)
        (r_package_dir / '{}.Rd'.format(dataset_meta['r_alias'])).write_text(rdata_rd)
        logging.info('Wrote docs to {} and {}'.format(output_dir, r_package_dir))

    def write_readme(self):
        """Generate the readme for the precinct-returns repo."""
        readme_template = self.env.get_template('precinct_readme.jinja')
        # Read variable metadata for the codebook. It doesn't matter which dataset we specify here; variables are the
        # same across the precinct datasets.
        dataset_meta = read_dataset_meta(Path('2016-precinct-house.yaml'), quietly=True)
        variable_meta = read_variable_meta(dataset_meta, quietly=True)
        # Read the coverage notes for precinct datasets
        coverage = yaml.load(dataset_meta_yaml_path('common/precinct-coverage.yaml').read_text())
        readme = readme_template.render(variables=variable_meta, states=coverage['coverage'])
        (precinct_returns_path() / 'README.md').write_text(readme)
        logging.info('Wrote precinct-returns readme to {}'.format(precinct_returns_path()))


def write_frequencies(df: pd.DataFrame, destination: str = '') -> pd.DataFrame:
    """Create a variable-value frequency table, optionally writing it to disk.
    """
    counts = {}
    for col in [var for var in df.columns.values if var != 'votes']:
        counts[col] = df[col].value_counts(dropna=False)
    count_dfs = []
    for k, v in counts.items():
        count_dfs.append(pd.DataFrame({'variable': k, 'count': v}).reset_index().rename({'index': 'value'}, axis=1))
    df = pd.concat(count_dfs)
    df = df[['variable', 'value', 'count']]
    df = df.sort_values(['variable', 'value', 'count'])
    df.reset_index(drop=True, inplace=True)
    if destination:
        df.to_csv(destination, index=False)
    return df


def r_alias(text: str) -> str:
    """Translate dataset names to valid R object names.

    Example: '2016-precinct-house' -> 'house_precinct_2016'.
    This is a Jinja filter. See http://jinja.pocoo.org/docs/2.10/api/#custom-filters.
    """
    if text:
        print(text)
        no_dashes = re.sub('[- ]', '_', text)
        return re.sub(r'([0-9]*)(_*)(.*)', '\g<3>\g<2>\g<1>', no_dashes)
    else:
        return ''


def format_code(text: str) -> str:
    """Translate `Markdown code` syntax to \code{Latex code} syntax.

    This is a Jinja filter. See http://jinja.pocoo.org/docs/2.10/api/#custom-filters.
    """
    if text:
        return re.sub(r'`([^`]+)`', '\code{\g<1>}', text)
    else:
        return ''


if __name__ == '__main__':
    docs = Documentation()
    for dataverse in DATAVERSE_SHORT_NAMES:
        docs.write(dataverse)
