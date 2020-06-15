#!/bin/bash

cd "$(dirname "$0")" || return 1

source ../other_scripts/get_conda_bin.sh

# shellcheck source=/Users/petioptrv/miniconda3/bin/activate
source "${CONDA_BIN}/activate" algotradepy

FAILED=0


pytest -s ../tests/connectors/test_ib_connector.py

if [ $? -ne 0 ]
then
  FAILED=1
fi

pytest -s ../tests/brokers/test_ib_broker.py

if [ $? -ne 0 ]
then
  FAILED=1
fi

if [ $FAILED -eq 1 ]
then
  echo "Tests failed. Fix them and run the script again."
  exit 1
else
  date +%s > ib_tests_run_ts
fi
