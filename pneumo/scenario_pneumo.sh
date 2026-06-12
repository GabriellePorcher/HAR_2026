#!/bin/sh
bindir=$(dirname "$0")
scenario=$(basename "$0" .sh)
cd ${bindir} ; env PYTHONPATH=.. python ${scenario}.py