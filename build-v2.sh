#!/bin/bash
# Update publications from temp list, then regenerate all HTML with jemdoc.
# Usage: ./build.sh   or   bash build.sh

set -e
cd "$(dirname "$0")"

echo "Step 1: Updating publications (index.jemdoc + publication.jemdoc)..."
python3 update_publications.py

echo "Step 2: Generating HTML (index, publication, teaching)..."
python3 jemdoc-v2.py index.jemdoc
python3 jemdoc-v2.py publication.jemdoc
python3 jemdoc-v2.py teaching.jemdoc

echo "Done."
