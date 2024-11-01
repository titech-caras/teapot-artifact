#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 [BINARY_NAME]" 1>&2
    exit
fi

export ASAN_OPTIONS=detect_leaks=0:verify_asan_link_order=false
cd "$(dirname $0)"/../../
BINARY_NAME=$1
TIMEFORMAT=%U
REPEAT=10

bench_program () {
    PROGRAM=$1
    for i in $(seq 1 $REPEAT); do $PROGRAM "teapot-testcases/resources/testcase/$BINARY_NAME.in" 1>/dev/null 2>/dev/null; done
}

ORIGINAL_TIME=$( { time bench_program "binaries/original/$BINARY_NAME"; } 2>&1)
TEAPOT_TIME=$( { time bench_program "binaries/teapot_nonest/$BINARY_NAME"; } 2>&1)
SPECFUZZ_TIME=$( { time bench_program "binaries/specfuzz/$BINARY_NAME"; } 2>&1)

echo "{ \"original\": \"$ORIGINAL_TIME\", \"teapot\": \"$TEAPOT_TIME\", \"specfuzz\": \"$SPECFUZZ_TIME\" }" >results/runtime/$BINARY_NAME.json
