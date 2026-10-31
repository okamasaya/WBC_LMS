#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--browser" ) ]]; then
  echo 'Usage: scripts/check-standard.sh [--browser]' >&2
  exit 2
fi
node scripts/audit-standard-runtime.mjs
for standard_test in tests/standard/*.test.mjs; do
  node "$standard_test"
done
if [[ "${1:-}" == "--browser" ]]; then
  node tests/standard/entry.browser.cjs
  node tests/standard/jsonDrill.browser.cjs
  node tests/standard/browser.cjs
  node tests/standard/styles.browser.cjs
fi
