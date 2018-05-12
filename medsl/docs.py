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
import plac
import yaml
from jinja2 import Environment, FileSystemLoader

from medsl.metadata import read_dataset_meta, read_variable_meta, read_dataverse_meta
from medsl.paths import dataset_output_path, precinct_yaml_paths, module_path, r_output_path, dataset_meta_yaml_path, \
    precinct_returns_path


class Documentation(object):
    pass


def write_docs(dataset: Path) -> (str, str):
    """Create documentation files for a dataset.

    As a side effect, writes dataset codebook, release notes, and R documentation to dataset_output_path().

    :param dataset: The Path of a YAML filename in metadata/dataset, e.g. '2016-precinct-senate.yaml'.
    :return A 2-tuple of (codebook, release notes) text.
    """
    template_loader = FileSystemLoader(searchpath=str(module_path / 'templates'))
    env = Environment(loader=template_loader)
    # The Rd template avoids using braces as delimiters
    rd_env = Environment(loader=template_loader, block_start_string='<+', block_end_string='+>',
                         variable_start_string='<<', variable_end_string='>>', comment_start_string='<#',
                         comment_end_string='>#')
    rd_env.filters['r_alias'] = r_alias
    rd_env.filters['format_code'] = format_code

    codebook_template = env.get_template('codebook.jinja')
    notes_template = env.get_template('release_notes.jinja')
    coverage_template = env.get_template('coverage_notes.jinja')
    rdata_template = rd_env.get_template('r_doc.jinja')

    # Load metadata for the dataset the codebook describes
    dataset_meta = read_dataset_meta(dataset, quietly=True)
    # Use today's date for version id
    dataset_meta['version'] = str(datetime.datetime.today().date())

    # Load metadata for the dataverse of the dataset
    dataverse_meta = read_dataverse_meta(dataset_meta['dataverse'])
    logging.debug('Read dataverse metadata: {}'.format(dataset_meta['dataverse']))

    # Load metadata for the variables in the dataset
    variable_meta = read_variable_meta(dataset_meta, quietly=True)
    del dataset_meta['variables']

    # Populate templates
    codebook = codebook_template.render(dataset=dataset_meta, dataverse=dataverse_meta, variables=variable_meta)
    notes = notes_template.render(dataset=dataset_meta)
    rdata_rd = rdata_template.render(dataset=dataset_meta, dataverse=dataverse_meta, variables=variable_meta)
    coverage = coverage_template.render(dataset=dataset_meta, states=dataset_meta['coverage'])

    # Destination directory is the name of the dataset YAML, less the .yaml extension,
    # e.g. '2016-precinct-president', under the path returned by dataset_output_path().
    output_dir = dataset_output_path(dataset)
    r_package_dir = r_output_path()

    # Write documentation to disk
    dataset_name = Path(dataset).stem
    (output_dir / 'codebook-{}.md'.format(dataset_name)).write_text(codebook)
    (output_dir / 'release-notes-{}.md'.format(dataset_name)).write_text(notes)
    (output_dir / 'coverage-notes-{}.md'.format(dataset_name)).write_text(coverage)
    (r_package_dir / '{}.Rd'.format(dataset_meta['r_alias'])).write_text(rdata_rd)
    print('Wrote docs to {} and {}'.format(output_dir, r_package_dir))

    return codebook, notes


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


def main():
    """Write dataset documentation.
    """
    # write_docs(Path('2016-precinct-house.yaml'))
    for yaml_path in precinct_yaml_paths():
        write_docs(yaml_path)


if __name__ == '__main__':
    # plac.call(write_docs, arglist=[Path('2016-precinct-house.yaml')])
    plac.call(main)
