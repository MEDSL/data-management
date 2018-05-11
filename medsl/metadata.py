# coding: utf-8
"""
Read and write to metadata files.

These files are in ./metadata and YAML-formatted.
"""

import yaml

from medsl.paths import dataset_meta_yaml_path, module_path


def update_dataset_meta(filename, replacements, quietly=False):
    """Replace metadata values in a YAML file."""
    path = module_path / 'metadata' / 'dataset' / filename
    meta = yaml.load(path.read_text())
    for k, v in replacements.items():
        meta[k] = v
        if not quietly:
            print('Replaced {}'.format(k))
    path.write_text(yaml.dump(meta, default_flow_style=False))


def read_dataset_meta(dataset, quietly=False):
    """Read metadata from the YAML file for a dataset, and any metadata inherited from other files.
    """
    if not quietly:
        print('Reading dataset metadata:')
    meta_yaml_path = dataset_meta_yaml_path(dataset)
    dataset_meta = yaml.load(meta_yaml_path.read_text())
    if not quietly:
        print('  {}'.format(dataset))
    if 'inherits' in dataset_meta:
        # The dataset inherits metadata from another file; read each of these
        for parent in dataset_meta['inherits']:
            # Descend into 'common' from the location of the dataset YAML and read the indicated parent
            inherited_meta = yaml.load((meta_yaml_path.parent / 'common' / parent).read_text())
            if not quietly:
                print('  {}'.format(parent))
            # Add the inherited metadata
            for k, v in inherited_meta.items():
                # But dataset metadata takes precedence; ignore existing keys
                if k not in dataset_meta:
                    dataset_meta[k] = v
    return dataset_meta


def read_variable_meta(dataset_meta, quietly=False):
    """Read metadata for all the variables in a dataset.

    We require from dataset_meta the keys 'variables' and 'variable_notes', if any.
    """
    # Load variable definitions. These are common to all election-returns datasets.
    variable_meta = yaml.load((module_path / 'metadata' / 'variables.yaml').read_text())
    # The 'variables' key of the dataset metadata is a list of the variables that appear in the dataset.
    # Filter definitions to those actually in the dataset.
    variable_meta = [var for var in variable_meta if var['name'] in dataset_meta['variables']]
    if 'variable_notes' in dataset_meta:
        if not quietly:
            print('Updating variable notes from dataset metadata:')
        for var in variable_meta:
            for note in dataset_meta['variable_notes']:
                if var['name'] == note['name']:
                    var['note'] = note['note']
                    if not quietly:
                        print('  {}'.format(var['name']))
    return variable_meta


def read_dataverse_meta(filestem):
    """Read dataverse metadata from YAML given the dataverse alias (e.g. 'medsl_senate')
    """
    path = module_path / 'metadata' / 'dataverse' / '{}.yaml'.format(filestem)
    return yaml.load(path.read_text())
