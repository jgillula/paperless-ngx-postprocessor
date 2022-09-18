#!/usr/bin/env bash

RUN_DIR=$( dirname -- "$( readlink -f -- "$0"; )"; )
source $RUN_DIR/venv/bin/activate
$RUN_DIR/post_consume_script.py
