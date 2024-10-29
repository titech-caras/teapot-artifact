#!/bin/bash

source "$(dirname "$0")"/common.sh
cd "$ROOTDIR"/teapot-testcases/jsmn

MY_CFLAGS="-O3"

# === Step 1: Compile original binaries ===
if [ -f fuzz ] ; then rm fuzz; fi
CC=clang CFLAGS="$MY_CFLAGS" make
mv fuzz "$ORIGINAL_BINARIES"/jsmn

# === Step 2: Compile binaries for SpecFuzz (1st pass) ===
FN_LIST=$(mktemp)

CC=clang-sf CFLAGS="--collect $FN_LIST $MY_CFLAGS" make

# === Step 3: Compile binaries for SpecFuzz (2nd pass) ===
rm fuzz
CC=clang-sf CFLAGS="--function-list $FN_LIST $MY_CFLAGS $SF_CFLAGS" make
mv fuzz "$SPECFUZZ_BINARIES"/jsmn

# === Step 4: Clean up the mess ===
rm $FN_LIST
