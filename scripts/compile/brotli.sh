#!/bin/bash

source "$(dirname "$0")"/common.sh
cd "$ROOTDIR"/teapot-testcases/brotli
./bootstrap

MY_CFLAGS="-O3 -Ic/include"

# === Step 1: Compile original binaries ===
if [ -f Makefile ] ; then make clean; fi
CC=clang CFLAGS="$MY_CFLAGS" ./configure --disable-shared
make -j$NUM_THREADS brotli_fuzz
mv brotli_fuzz "$ORIGINAL_BINARIES"/brotli

# === Step 2: Compile binaries for SpecFuzz (1st pass) ===
FN_LIST=$(mktemp)

make clean
CC=clang-sf CFLAGS="--collect $FN_LIST $MY_CFLAGS" ./configure --disable-shared
sed -i 's/brotli\\ 1\.0\.7/brotli_1.0.7/g' Makefile # to make SpecFuzz happy
make -j$NUM_THREADS brotli_fuzz

# === Step 3: Compile binaries for SpecFuzz (2nd pass) ===
make clean
CC=clang-sf CFLAGS="--function-list $FN_LIST $MY_CFLAGS $SF_CFLAGS" ./configure --disable-shared
sed -i 's/brotli\\ 1\.0\.7/brotli_1.0.7/g' Makefile
make -j$NUM_THREADS brotli_fuzz
mv brotli_fuzz "$SPECFUZZ_BINARIES"/brotli

# === Step 4: Clean up the mess ===
make clean
rm $FN_LIST
