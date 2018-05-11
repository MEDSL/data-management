# coding: utf-8
"""
Create R package datasets (rda files).

The approach is to write the DataFrame to disk as feather, and then read that file into R and write it back as rda.

This relies on system calls to R, which is fragile, but rpy2 choked on the DataFrames.
"""
import subprocess
from pathlib import Path

from rpy2 import robjects
from rpy2.robjects import pandas2ri

from medsl.paths import dataset_rda_path, module_path

pandas2ri.activate()


def file_to_rda(input_path: Path,
                output_path: Path,
                r_alias: str,
                script_name: str = 'feather_to_rda.R') -> subprocess.CompletedProcess:
    """Make a system call to an R script that reads a data file and writes it to an Rda.
    """
    r_call = [
        str(Path('/usr/bin/Rscript').resolve()),
        str(module_path / script_name),
        str(input_path.resolve()),
        r_alias,
        str(output_path),
    ]
    return subprocess.run(r_call)


def pandas_to_rda(df, path):
    """Write a Pandas DataFrame to an rda.
    """
    r_dataframe = pandas2ri.py2ri(df)
    robjects.globalenv['df'] = r_dataframe
    robjects.r['save']('df', file=path)
