#!/bin/bash

source "$(dirname "$0")"/common.sh
cd "$ROOTDIR"/teapot-testcases/yaml
autoreconf -fvi

MY_CFLAGS="-O3"

# === Step 1: Compile original binaries ===
if [ -f Makefile ] ; then make clean; fi
CC=clang CFLAGS="$MY_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS
mv tests/fuzz "$ORIGINAL_BINARIES"/yaml

# === Step 2: Compile binaries for SpecFuzz (1st pass) ===
FN_LIST=$(mktemp)

make clean
CC=clang-sf CFLAGS="--collect $FN_LIST $MY_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS

# === Step 3: Compile binaries for SpecFuzz (2nd pass) ===
make clean
CC=clang-sf CFLAGS="--function-list $FN_LIST $MY_CFLAGS $SF_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS
mv tests/fuzz "$SPECFUZZ_BINARIES"/yaml

# === Step 4: Clean up the mess ===
make clean
rm $FN_LIST
