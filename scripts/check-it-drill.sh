#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--browser" ) ]]; then
    echo 'Usage: bash scripts/check-it-drill.sh [--browser]' >&2
    exit 2
fi
node --test tests/drill_IT/*.test.mjs
if [[ "${1:-}" == "--browser" ]]; then
    node tests/drill_IT/browser.cjs
    node tests/drill_IT/genai_261111.browser.cjs
    node tests/drill_IT/polarity_demo.browser.cjs
fi
