#!/bin/bash

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 [BINARY_FILE]" 1>&2
    exit
fi

if [[ ! -x "$(which teapot)" ]]; then
    echo "Cannot find teapot executable! Might have been executed in the wrong container" 1>&2
    exit
fi

cd "$(dirname \"$0\")"
BINARY_NAME=$1
WORKDIR=$(mktemp -d)

ddisasm --ir "$WORKDIR/$BINARY_NAME.gtirb" "binaries/original/$BINARY_NAME"
teapot "$WORKDIR/$BINARY_NAME.gtirb" "$WORKDIR/$BINARY_NAME.inst.gtirb"
gtirb-pprinter --ir "$WORKDIR/$BINARY_NAME.inst.gtirb" --asm "$WORKDIR/$BINARY_NAME.inst.S"
sed -i -f /teapot-scripts/fix_asm.sed "$WORKDIR/$BINARY_NAME.inst.S" 

LINKER_ARGS="-lhfuzz -lasan -lm -lz"

gcc -o "binaries/teapot/$BINARY_NAME"  "$WORKDIR/$BINARY_NAME.inst.S" -no-pie -nostartfiles -lcheckpoint_x64 $LINKER_ARGS
gcc -o "binaries/teapot_nonest/$BINARY_NAME"  "$WORKDIR/$BINARY_NAME.inst.S" -no-pie -nostartfiles -lcheckpoint_x64_nonest $LINKER_ARGS

rm -rf "$WORKDIR"
