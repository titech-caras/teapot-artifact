#!/bin/bash

source "$(dirname "$0")"/common.sh
cd "$ROOTDIR"/teapot-testcases/openssl

MY_CFLAGS="-O3"
CONFIG_FLAGS="no-asm no-shared no-threads no-fips no-legacy no-tests enable-fuzz-afl enable-tls1_3 enable-weak-ssl-ciphers enable-rc5 enable-md2 enable-ssl3 enable-ssl3-method enable-nextprotoneg"

# === Step 1: Compile original binaries ===
if [ -f Makefile ] ; then make clean; fi
./config $CONFIG_FLAGS CC=clang CFLAGS="$MY_CFLAGS"
make -j$NUM_THREADS
mv fuzz/server "$ORIGINAL_BINARIES"/openssl

# === Step 2: Compile binaries for SpecFuzz (1st pass) ===
FN_LIST=$(mktemp)

make clean
./config $CONFIG_FLAGS CC=clang-sf CFLAGS="--collect $FN_LIST $MY_CFLAGS"
make -j$NUM_THREADS

# === Step 3: Compile binaries for SpecFuzz (2nd pass) ===
make clean
./config $CONFIG_FLAGS CC=clang-sf CFLAGS="--function-list $FN_LIST $MY_CFLAGS $SF_CFLAGS"
make -j$NUM_THREADS
mv fuzz/server "$SPECFUZZ_BINARIES"/openssl

# === Step 4: Clean up the mess ===
make clean
rm $FN_LIST
