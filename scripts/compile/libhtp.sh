#!/bin/bash

source "$(dirname "$0")"/common.sh
cd "$ROOTDIR"/teapot-testcases/libhtp
./autogen.sh

MY_CFLAGS="-O3"

# === Step 1: Compile original binaries ===
if [ -f Makefile ] ; then make clean; fi
CC=clang CFLAGS="$MY_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS
make -j$NUM_THREADS -C test test_fuzz
mv test/test_fuzz "$ORIGINAL_BINARIES"/libhtp

# === Step 2: Compile binaries for SpecFuzz (1st pass) ===
FN_LIST=$(mktemp)

make clean
CC=clang-sf CFLAGS="--collect $FN_LIST $MY_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS
make -j$NUM_THREADS -C test test_fuzz

# === Step 3: Compile binaries for SpecFuzz (2nd pass) ===
make clean
CC=clang-sf CFLAGS="--function-list $FN_LIST $MY_CFLAGS $SF_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS
make -j$NUM_THREADS -C test test_fuzz
mv test/test_fuzz "$SPECFUZZ_BINARIES"/libhtp

# === Step 4: Clean up the mess ===
make clean
rm $FN_LIST
