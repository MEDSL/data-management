# Codebook for U.S. President 1976–2016

URL: https://dx.doi.org/10.7910/DVN/42MVDX

Version: 2018-03-11T22:23:09Z

This codebook describes a dataset on constituency-level returns for elections
to the U.S. presidency.

Each record in the dataset gives the number of votes reported in a constituency
for a candidate.

The data source is the document "[Statistics of the Congressional
Election](http://history.house.gov/Institution/Election-Statistics/Election-
Statistics/)," published biennially by the Clerk of the U.S. House of
Representatives.

## Variables

The dataset contains the following variables:

- `year`
- `state`
- `state_postal`
- `state_fips`
- `state_census`
- `state_icpsr`
- `office`
- `district`
- `stage`
- `special`
- `candidate`
- `writein`
- `party`
- `votes`


### year

Year of election.



### state

State name.



### state_postal

State U.S. Postal Service abbreviation, or two-letter ISO 1366 code.



### state_fips

Numeric state FIPS 5-2 code.



### state_census

Numeric U.S. Census state code.



### state_icpsr

Numeric ICPSR state code.



### office

The office for which the `candidate` ran.



### district

District associated with the `office`, where applicable.

Not applicable in presidential elections.


### stage

The electoral stage, either `gen` for general elections or `pri` for primary
elections.



### special

Whether the election was a special election, either `TRUE` for special
elections or `FALSE` otherwise.



### candidate

The name of the candidate.



### writein

Whether the record describes a write-in candidate, either `TRUE` or `FALSE`.



### party

Party of the `candidate`, where applicable. Candidates may run on multiple
party lines, so to compute two-party vote shares or candidate vote totals,
aggregate over `party`.



### votes

Number of votes received.
