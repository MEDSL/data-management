# coding: utf-8
"""
Read YAML-formatted metadata files from ./metadata.
"""

import datetime
import logging

import yaml

from medsl.paths import dataset_meta_yaml_path, module_path


class Metadata(object):
    """Metadata for precinct returns.
    """

    def __init__(self, dataverse):
        self.dataverse = dataverse
        self.dataset_yaml = dataset_meta_yaml_path('2016-precinct-{}.yaml'.format(dataverse))
        self.dataset_meta = self._read_dataset_yaml()
        self.variable_meta = self._read_variable_yaml()
        self.dataverse_meta = self._read_dataverse_yaml()
        self.coverage = self._read_coverage()
        # Use today's date as version
        self.dataset_meta['version'] = str(datetime.datetime.today().date())

    def _read_dataset_yaml(self):
        """Read metadata from the YAML file for a dataset, and any metadata inherited from other files.
        """
        dataset_meta = yaml.load(self.dataset_yaml.read_text())
        if 'inherits' in dataset_meta:
            # The dataset inherits metadata from another file; read each of these
            for inherited in dataset_meta['inherits']:
                # Descend into 'common' from the location of the dataset YAML and read the indicated file
                inherited_meta = yaml.load((self.dataset_yaml.parent / 'common' / inherited).read_text())
                # Add the inherited metadata
                for k, v in inherited_meta.items():
                    # But dataset metadata takes precedence; ignore existing keys
                    if k not in dataset_meta:
                        dataset_meta[k] = v
        return dataset_meta

    def _read_variable_yaml(self):
        """Read metadata for all the variables in a dataset.

        We require from dataset_meta the keys 'variables' and 'variable_notes', if any.
        """
        # Load variable definitions. These are common to all election-returns datasets.
        variable_meta = yaml.load((module_path / 'metadata' / 'variables.yaml').read_text())
        # The 'variables' key of the dataset metadata is a list of the variables that appear in the dataset.
        # Filter definitions to those actually in the dataset.
        variable_meta = [var for var in variable_meta if var['name'] in self.dataset_meta['variables']]
        if 'variable_notes' in self.dataset_meta:
            logging.debug('Updating variable notes from dataset metadata:')
            for var in variable_meta:
                for note in self.dataset_meta['variable_notes']:
                    if var['name'] == note['name']:
                        var['note'] = note['note']
                        logging.debug('  {}'.format(var['name']))
        return variable_meta

    def _read_dataverse_yaml(self):
        """Read dataverse metadata from YAML given the dataverse alias (e.g. 'medsl_senate')
        """
        path = self.dataset_yaml.parent.parent / 'dataverse' / 'medsl_{}.yaml'.format(self.dataverse)
        return yaml.load(path.read_text())

    def _read_coverage(self):
        return yaml.load(dataset_meta_yaml_path('common/precinct-coverage.yaml').read_text())
