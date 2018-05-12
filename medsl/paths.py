# coding: utf-8
"""
Resolve paths to data.

These functions encode file naming conventions.
"""

from pathlib import Path

import medsl

module_path = Path(medsl.__file__).parent.resolve()


def dataset_output_path(dataset_yaml_path: Path) -> Path:
    """Get the path to the output directory for release-ready files."""
    p = module_path.parent.parent / 'precinct-returns' / dataset_yaml_path.stem
    return p.resolve()


def precinct_returns_path() -> Path:
    """Get the path to the precinct-returns repo."""
    p = module_path.parent.parent / 'precinct-returns'
    return p.resolve()


def dataset_source_path() -> Path:
    """Get the path to the directory for dataset source files."""
    p = precinct_returns_path() / 'source'
    return p.resolve()


def openelections_path() -> Path:
    """Get the path to the directory for OpenElections repos.

    Expected at ../../openelections.
    """
    p = module_path.parent.parent / 'openelections'
    return p.resolve()


def dataset_csv_path(dataset_yaml_path: Path) -> Path:
    """Get the path for a release-ready CSV."""
    output_path = dataset_output_path(dataset_yaml_path)
    p = output_path / '{}.csv'.format(dataset_yaml_path.stem)
    return p.resolve()


def precinct_data_path() -> Path:
    """Get the path to the 2016-precinct-data data directory.

    Expected at ../../2016-precinct-data/data.
    """
    p = module_path.parent.parent / '2016-precinct-data' / 'data'
    return p.resolve()


def state_csv_path(state_abbr: str) -> Path:
    """Get the path for a final state CSV."""
    p = precinct_data_path() / state_abbr.upper() / 'final' / '2016-{}-precinct.csv'.format(state_abbr.lower())
    return p.resolve()


def r_output_path() -> Path:
    """Get the path to the directory for release-ready R package files."""
    p = module_path / 'output' / 'r-package'
    return p.resolve()


def dataset_rda_path(r_alias: str) -> Path:
    """Get the path for a release-ready rda."""
    p = r_output_path() / '{}.rda'.format(r_alias)
    return p.resolve()


def precinct_yaml_paths() -> list:
    """Get an iterable of paths to the YAML metadata for 2016 precinct datasets."""
    p = module_path / 'metadata' / 'dataset'
    return p.resolve().glob('2016-precinct*.yaml')


def dataset_meta_yaml_path(dataset_name: str) -> Path:
    """Get the path to a dataset's YAML metadata file."""
    p = module_path / 'metadata' / 'dataset' / dataset_name
    return p.resolve()
