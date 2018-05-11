# data management

This repo provides code and metadata for releasing [MEDSL datasets](https://electionlab.mit.edu/data).

We use the `medsl` module to:

- Validate precinct-level returns from each state
- Combine and transform these returns into release-ready datasets
- Generate accompanying documentation
- Update the [`elections`](https://github.com/MEDSL/elections) R package


## use

To generate docs and datasets:

```bash
$ python release.py
```

We assume the following directory structure:

```
├── 2016-precinct-data
├── data-management
├── elections
└── precinct-returns
```

Where:

* `2016-precinct-data` contains input data, the returns for each state (not yet available online);
* `data-management` is this repository;
* `elections` contains our [R package](https://github.com/MEDSL/elections) for election data, and is an output target;
* `precinct-returns` is the repo for [released datasets](https://github.com/MEDSL/precinct-returns), and is an output target.


## installation

Requires Python 3. Not yet tested on anything but Fedora Linux and Python 3.6,
but should be fine on MacOS.

`virtualenv` installation:

```
$ git clone git@github.com:MEDSL/data-management.git data-management
$ cd data-management
$ python3 -m virtualenv env -p python3
$ source env/bin/activate
$ pip install -r medsl/requirements.txt
```

The `feather-format` library depends on `pyarrow`, whose availability on pip
varies by platform
([instructions](https://github.com/wesm/feather/tree/master/python#installing)). 

