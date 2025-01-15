#!/bin/bash
# Author: kongexp
# Date: 2025-01-14

function show_help {
    echo "Usage: $0 [pack|unpack|help] [file_or_directory]"
    echo "  pack   - Compress and split the specified file or directory."
    echo "  unpack - Reassemble and decompress the archive in the specified directory."
    echo "  help   - Show this help message"
}

function normalize_path {
    local path="$1"
    # Remove leading './' if present
    path="${path#./}"
    echo "$path"
}

function pack {
    local path=$(normalize_path "$1")
    local dir=$(dirname "$path")
    local base=$(basename "$path")

    cd "$dir" || exit
    tar cvf - "$base" | pzstd - > "$base.tar.zst" && \
    rm -rf "$base" && \
    split -b 99M "$base.tar.zst" "${base}.tar.zst_part_" && \
    rm -rf "$base.tar.zst"
    cd - > /dev/null
}

function unpack {
    local path=$(normalize_path "$1")
    local dir=$(dirname "$path")
    local base=$(basename "$path")

    cd "$dir" || exit
    cat "${base}.tar.zst_part_"* > "$base.tar.zst" && \
    pzstd -d "$base.tar.zst" && \
    rm "$base.tar.zst" && \
    rm "${base}.tar.zst_part_"* && \
    tar xvf "$base.tar" && \
    rm "$base.tar"
    cd - > /dev/null
}

if [ "$1" == "pack" ]; then
    if [ -z "$2" ]; then
        echo "Error: No file or directory specified for packing."
        show_help
        exit 1
    fi
    pack "$2"
elif [ "$1" == "unpack" ]; then
    if [ -z "$2" ]; then
        echo "Error: No file or directory specified for unpacking."
        show_help
        exit 1
    fi
    unpack "$2"
else
    show_help
fi
