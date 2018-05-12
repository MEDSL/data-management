#!/usr/bin/env python3
# coding: utf-8
"""
Prepare for release the precinct-level data in the '2016-precinct-data' directory.
"""
import logging
import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import feather
import pandas as pd
import pyarrow
import yaml

from medsl import PRECINCT_COLS, DATAVERSE_SHORT_NAMES
from medsl.docs import Documentation, write_frequencies
from medsl.metadata import Metadata
from medsl.paths import dataset_csv_path, state_csv_path, dataset_meta_yaml_path, precinct_returns_source_dir, \
    module_path, dataset_output_path
from medsl.rdas import file_to_rda


class PrecinctData(object):
    """A data class for precinct-level election returns.

    This class reads normalized precinct returns for a set of states from the disk, and combines them into a single
    DataFrame. By default states marked as ready for release (included=True) in `precinct-coverage.yaml` are
    included. The result is available via the `precinct_returns` attribute. Our published datasets are subsets (
    proper and overlapping) of this DataFrame. The Dataset class takes PrecinctData as input and is responsible for
    taking a subset and writing it to disk with documentation.

    Calling the `copy_state_csvs` method populates the `precinct-returns/source` directory with the state CSVs (
    copied from the state directories and zipped for GitHub).
    """

    def __init__(self, state_postals=None):
        """
        :param state_postals: Postal abbreviations for states to include. By default, states with included=True in
        `precinct-coverage.yaml` will be included.
        """
        self.coverage = yaml.load(dataset_meta_yaml_path('common/precinct-coverage.yaml').read_text())
        state_ids = pd.read_csv(module_path / 'gazetteers' / 'states.csv')
        if state_postals:
            # Include specified states, regardless of how precinct data coverage is defined
            self.state_postals = state_postals
            # Walk from state postal abbreviations to state names
            self.state_names = list(state_ids.loc[state_ids.state_postal.isin(state_ids), 'state'].values)
        else:
            # Include states with included=True in `precinct-coverage.yaml`
            self.state_names = [k for k, v in self.coverage.items() if v['included']]
            # Walk from state names to state postal abbreviations for use in paths
            self.state_postals = list(state_ids.loc[state_ids.state.isin(self.state_names), 'state_postal'].values)
        self.precinct_returns = self.read_precincts()

    def copy_state_csvs(self):
        """Copy the state CSVs to a `sources` subdirectory of the output directory.
        """
        for state_postal in self.state_postals:
            self.copy_precinct_csv(state_postal)

    def read_precincts(self) -> pd.DataFrame:
        """Read precinct-level returns for all states indicated in the state_postals attribute.
        """
        precinct_returns = pd.concat([self.read_precinct_csv(state) for state in self.state_postals])
        # Select and reorder columns; sort rows
        precinct_returns = precinct_returns[list(PRECINCT_COLS)]
        sort_order = ['dataverse', 'state', 'jurisdiction', 'precinct', 'candidate', 'party']
        precinct_returns = precinct_returns.sort_values(sort_order)
        return precinct_returns

    @staticmethod
    def read_precinct_csv(state_abbr: str) -> pd.DataFrame:
        """Given a state postal abbreviation, read the corresponding precinct-level returns."""
        csv_path = state_csv_path(state_abbr)
        logging.debug('Reading {}'.format(csv_path))
        try:
            df = pd.read_csv(csv_path, dtype=PRECINCT_COLS, low_memory=False, index_col=False)
        except UnicodeDecodeError:
            logging.error('UnicodeDecodeError reading {}'.format(csv_path))
            df = pd.read_csv(csv_path, dtype=PRECINCT_COLS, low_memory=False, encoding='latin1', index_col=False)
        except FileNotFoundError as e:
            logging.error('No file for {}: {}'.format(state_abbr, e))
            df = pd.DataFrame()
        except ValueError as e:
            # Re-read without dtypes to get column names for debugging
            headers = pd.read_csv(csv_path, nrows=0)
            logging.error('Reading {} with columns {}'.format(state_abbr, headers.columns.values))
            raise e
        return df

    @staticmethod
    def copy_precinct_csv(state_abbr: str, zip=True) -> None:
        """Copy final CSVs from state directories into precinct-returns/source directory.
        """
        state_csv = state_csv_path(state_abbr)
        dataset_csv = precinct_returns_source_dir / state_csv.name
        shutil.copy2(state_csv, dataset_csv)
        if zip:
            with ZipFile(dataset_csv.with_suffix('.zip'), 'w', ZIP_DEFLATED) as zip:
                zip.write(dataset_csv, dataset_csv.name)


class Dataset(object):
    """A class for precinct return datasets.

    The DataFrame holding the data is in the `table` attribute. The `release` method writes the dataset and its
    documentation to disk.
    """

    def __init__(self, precinct_data: PrecinctData, dataverse: str):
        """Subset PrecinctData, resolve output paths, and read dataset metadata.

        :param precinct_data: PrecinctData for one or more states.
        :param dataverse: The short name for a dataverse: 'president', 'senate', 'house', 'state', or 'local'.
        """
        self.dataverse = dataverse
        # Subset from all the precinct data to rows assigned to the dataverse, or included in all dataverses
        subset = precinct_data.precinct_returns.loc[
            precinct_data.precinct_returns['dataverse'].isin([self.dataverse, 'all'])]
        # Don't include the dataverse column, used only for this subsetting, in the release data
        del subset['dataverse']
        self.table = subset
        # Resolve output paths
        self.yaml_file = Path('2016-precinct-{}.yaml'.format(self.dataverse))
        self.output_path = dataset_output_path(self.yaml_file)
        self.csv_path = dataset_csv_path(self.yaml_file)
        self.feather_path = self.csv_path.with_suffix('.feather')
        self.rda_path = self.csv_path.with_suffix('.rda')
        self.frequencies_path = self.output_path / 'frequencies-{}.csv'.format(self.csv_path.stem)
        # Read associated metadata
        self.metadata = Metadata(dataverse)

    def release(self) -> None:
        """Write a dataset and its documentation to disk.
        """
        # Write release files to output directory
        if not self.csv_path.parent.exists():
            self.csv_path.parent.mkdir()
        self.table.to_csv(self.csv_path, index=False)
        self.write_feather(self.table)
        write_frequencies(self.table, str(self.frequencies_path))
        Documentation().write(self.dataverse)

        # Zip the output files
        with ZipFile(self.csv_path.with_suffix('.zip'), 'w', ZIP_DEFLATED) as zip:
            zip.write(self.csv_path, self.csv_path.name)
            zip.write(self.frequencies_path, self.frequencies_path.name)
            [zip.write(doc_path, doc_path.name) for doc_path in self.csv_path.parent.glob('*.md')]

        # Validate docs
        self.check_documentation(self.table)

    def write_feather(self, subset: pd.DataFrame) -> None:
        try:
            # Write feather
            subset.reset_index(inplace=True, drop=True)
            feather.write_dataframe(subset, self.feather_path)
            # Write rda from feather
            file_to_rda(self.feather_path, self.rda_path, self.metadata.dataset_meta['r_alias'], 'feather_to_rda.R')
            logging.info('Wrote data to {}'.format(self.feather_path.parent))
        except pyarrow.lib.ArrowInvalid:
            logging.error('Error writing {} subset as feather:'.format(self.dataverse))
            # We see this error when attempting to write 'object' dtypes that can't be mapped to feather types
            self.find_mixed_type_columns(subset)

    def find_mixed_type_columns(self, subset):
        """Find columns that can't be written as feather.
        """
        mixed_cols = []
        for col in subset.columns:
            try:
                feather.write_dataframe(subset[[col]], '/dev/null')
            except pyarrow.lib.ArrowInvalid:
                mixed_cols.append(col)
        if mixed_cols:
            logging.error('pyarrow error from mixed-type column: {}'.format('; '.join(mixed_cols)))
            return mixed_cols

    def check_documentation(self, subset: pd.DataFrame) -> None:
        """Assert that all variables in data are documented, and no others.
        """
        subset_cols = set(subset.columns.values)
        doc_cols = {col['name'] for col in self.metadata.variable_meta}
        not_in_docs = subset_cols - doc_cols
        not_in_data = doc_cols - subset_cols
        msg = ''
        if not_in_docs:
            msg += 'Undocumented variables in {}: {}. '.format(self.metadata.dataverse, not_in_docs)
        if not_in_data:
            msg += 'Documented variables missing from {}: {}.'.format(self.metadata.dataverse, not_in_docs)
        if msg:
            raise ValueError(msg)


if __name__ == '__main__':
    precinct_data = PrecinctData()
    precinct_data.copy_state_csvs()
    Documentation().write_readme()
    for dataverse in DATAVERSE_SHORT_NAMES:
        dataset = Dataset(precinct_data, dataverse)
        dataset.release()
