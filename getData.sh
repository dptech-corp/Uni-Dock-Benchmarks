#!/bin/bash
set -e  # exit on failure

DOWNLOAD_URL="https://bohrium-api.dp.tech/ds-dl/udbench-o67b-v1.zip"
ZIP_FILE="tmp_data.zip"
TMP_DIR="tmp_data_extract"
FINAL_DIR="data"
EXPECTED_SHA256=""  # TODO: fill in after first download, e.g. "a1b2c3d4..."

echo "Downloading data archive..."
if ! { curl -L -o "$ZIP_FILE" "$DOWNLOAD_URL" || wget -O "$ZIP_FILE" "$DOWNLOAD_URL"; }; then
    echo "Download failed, please check internet connection and the URL."
    exit 1
fi

if [ -n "$EXPECTED_SHA256" ]; then
    echo "Verifying SHA256 checksum..."
    ACTUAL_SHA256=$(sha256sum "$ZIP_FILE" | awk '{print $1}')
    if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
        echo "ERROR: SHA256 checksum mismatch!"
        echo "  Expected: $EXPECTED_SHA256"
        echo "  Actual:   $ACTUAL_SHA256"
        echo "The downloaded file may be corrupted. Aborting."
        rm -f "$ZIP_FILE"
        exit 1
    fi
    echo "Checksum OK."
else
    echo "WARNING: No expected SHA256 configured, skipping checksum verification."
    echo "  Actual SHA256: $(sha256sum "$ZIP_FILE" | awk '{print $1}')"
fi

echo "Extracting archive..."
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
unzip -oq "$ZIP_FILE" -d "$TMP_DIR"
rm -f "$ZIP_FILE"

echo "Preparing ./$FINAL_DIR ..."
if [ -d "$FINAL_DIR" ]; then
    echo "WARNING: ./$FINAL_DIR already exists and will be REPLACED."
    read -r -p "Continue? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted. Extracted data is kept in ./$TMP_DIR"
        exit 0
    fi
    rm -rf "$FINAL_DIR"
fi

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
