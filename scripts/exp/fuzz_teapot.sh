#!/bin/bash

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 [BINARY_NAME] [RUN_TIME]" 1>&2
    exit
fi

export ASAN_OPTIONS=detect_leaks=0:verify_asan_link_order=false
cd "$(dirname $0)"/../../
BINARY_NAME=$1
RUN_TIME=$2
THREADS=8

if [[ "$BINARY_NAME" == "yaml" ]]; then
    # yaml doesn't have an inital corpora but rather a dictionary
    EXTRA_ARGS="-w teapot-testcases/resources/seed/yaml.dict"
fi

WORKDIR=$(mktemp -d)
cp "teapot-testcases/resources/seed/$BINARY_NAME/"* $WORKDIR/

honggfuzz $EXTRA_ARGS -l $WORKDIR/hongg.log --run_time $RUN_TIME -n $THREADS --no_fb_timeout 1 --timeout $RUN_TIME \
    -f $WORKDIR -W $WORKDIR -Q --linux_no_ptrace -- "binaries/teapot/$BINARY_NAME" ___FILE___ 2>&1 | \
    python3 scripts/exp/fuzz_teapot_analyzer.py collect -o "results/fuzz/teapot/$BINARY_NAME.json"

rm -rf "$WORKDIR"
