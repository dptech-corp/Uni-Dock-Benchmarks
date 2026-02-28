#!/bin/bash
set -e  # exit on failure

DOWNLOAD_URL="https://bohrium-api.dp.tech/ds-dl/udbench-o67b-v1.zip"
ZIP_FILE="tmp_data.zip"
TMP_DIR="tmp_data_extract"
FINAL_DIR="data"

echo "Downloading data archive..."
if ! { curl -L -o "$ZIP_FILE" "$DOWNLOAD_URL" || wget -O "$ZIP_FILE" "$DOWNLOAD_URL"; }; then
    echo "Download failed, please check internet connection and the URL."
    exit 1
fi

echo "Extracting archive..."
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
unzip -oq "$ZIP_FILE" -d "$TMP_DIR"
rm -f "$ZIP_FILE"

echo "Preparing ./$FINAL_DIR ..."
rm -rf "$FINAL_DIR"

if [ -d "$TMP_DIR/$FINAL_DIR" ]; then
    mv "$TMP_DIR/$FINAL_DIR" "$FINAL_DIR"
else
    mapfile -t TOP_LEVEL_DIRS < <(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d)
    mapfile -t TOP_LEVEL_ENTRIES < <(find "$TMP_DIR" -mindepth 1 -maxdepth 1)

    if [ "${#TOP_LEVEL_ENTRIES[@]}" -eq 1 ] && [ "${#TOP_LEVEL_DIRS[@]}" -eq 1 ]; then
        mv "${TOP_LEVEL_DIRS[0]}" "$FINAL_DIR"
    else
        mkdir -p "$FINAL_DIR"
        shopt -s dotglob nullglob
        mv "$TMP_DIR"/* "$FINAL_DIR"/
        shopt -u dotglob nullglob
    fi
fi

rm -rf "$TMP_DIR"

echo "Done! Data is available at ./$FINAL_DIR"
