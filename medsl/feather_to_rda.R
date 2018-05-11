#!/usr/bin/Rscript
# coding: utf-8
#
# Save a feather file as an Rda file.
# 
# Takes three positional command-line arguments:
#   1. Path to input feather
#   2. Name to assign the dataframe created from the input feather
#   3. Path to output Rda
#
# Called from `rdas.py`.

# input_path = 'output/2016-precinct-local/2016-precinct-local.feather'
# r_alias = 'local_precinct_2016'
# output_path = 'test.rda'

suppressPackageStartupMessages(library(data.table))
suppressPackageStartupMessages(require(feather))
suppressPackageStartupMessages(library(assertthat))
suppressPackageStartupMessages(library(glue))

args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
r_alias <- args[2]
output_path <- args[3]

sink('/dev/null')

assert_that(is.string(r_alias))
assert_that(is.string(input_path))
assert_that(is.string(output_path))
assert_that(file.exists(input_path))

input <- feather::read_feather(input_path)
message(glue('Read {input_path}'))
setDT(input)

assert_that(!any(is.na(input$votes)), msg =
  glue('NA votes at {i}', i = paste(which(is.na(input$votes)), collapse = ', ')))
assert_that(all(input$votes %% 1 == 0), msg =
  glue('Non-integer votes at {i}', i = which(input$votes %% 1 != 0)))

input[, votes := as.integer(votes)]

sink()

assign(r_alias, input)
save(list = r_alias, file = output_path, compress = "bzip2")
