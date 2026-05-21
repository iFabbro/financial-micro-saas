#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE="$ROOT/output/release_bundle"

if [[ ! -d "$BUNDLE" ]]; then
  echo "release bundle not found: $BUNDLE" >&2
  exit 1
fi

rm -rf "$BUNDLE/tests" \
       "$BUNDLE/src"/*.bak* \
       "$BUNDLE/db/financial_data.db.bak*" \
       "$BUNDLE/output/health_check_report.json" \
       "$BUNDLE/math_core.py"

find "$BUNDLE" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$BUNDLE" -type f -name '*.pyc' -delete
find "$BUNDLE" -type f -name '*.bak*' -delete

echo "cleaned: $BUNDLE"
