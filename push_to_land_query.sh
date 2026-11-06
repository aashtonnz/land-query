#!/usr/bin/env bash
set -euo pipefail
# One-command push script for https://github.com/aashtonnz/land-query
# Usage: Unzip land-query-v39.0-repo.zip, cd into land-query, and run:
#   bash push_to_land_query.sh

git remote set-url origin https://github.com/aashtonnz/land-query.git 2>/dev/null || git remote add origin https://github.com/aashtonnz/land-query.git
git branch -M main
echo "Pushing TopoNZ / TopoAU v39.0 (96 Domains, 2,746 Primitives) to https://github.com/aashtonnz/land-query ..."
git push -u origin main
echo "Done! Your repo is live at https://github.com/aashtonnz/land-query"
