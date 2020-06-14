#!/bin/bash

# adaptation of https://github.com/CoinAlpha/hummingbot/blob/master/install

cd "$(dirname "$0")" || return 1

# Compatibility logic for older Anaconda versions.
if [ "${CONDA_EXE} " == " " ]; then
    CONDA_EXE=$( (find /opt/conda/bin/conda || find ~/anaconda3/bin/conda || \
	    find /usr/local/anaconda3/bin/conda || find ~/miniconda3/bin/conda  || \
	    find /root/miniconda/bin/conda || find ~/Anaconda3/Scripts/conda) \
	    2>/dev/null)
fi
if [ "${CONDA_EXE}_" == "_" ]; then
    echo "Please install Anaconda w/ Python 3.7+ first"
    echo "See: https://www.anaconda.com/distribution/"
    exit 1
fi
CONDA_BIN=$(dirname "${CONDA_EXE}")
ENV_FILE=setup/environment.yml  # TODO: make file

if ${CONDA_EXE} env list | grep -Eqe "^algotradepy"; then
    ${CONDA_EXE} env update -f $ENV_FILE
else
    ${CONDA_EXE} env create -f $ENV_FILE
fi

source "${CONDA_BIN}/activate" algotradepy

pre-commit install
versioneer install