#!/bin/bash

# adaptation of https://github.com/CoinAlpha/hummingbot/blob/master/install

cd "$(dirname "$0")" || return 1

source other_scripts/get_conda_bin.sh

ENV_FILE=environment.yml  # TODO: make file

if ${CONDA_EXE} env list | grep -Eqe "^algotradepy"; then
    ${CONDA_EXE} env update -f $ENV_FILE
else
    ${CONDA_EXE} env create -f $ENV_FILE
fi

# shellcheck source=/Users/petioptrv/miniconda3/bin/activate
source "${CONDA_BIN}/activate" algotradepy

pre-commit install
versioneer install
cp other_scripts/pre-push .git/hooks/pre-push