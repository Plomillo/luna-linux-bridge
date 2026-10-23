#!/usr/bin/env bash
set -euo pipefail

command -v python >/dev/null || { echo 'Python 3.11-3.13 is required for Skyvern.'; exit 1; }
command -v node >/dev/null || { echo 'Node.js 20+ is required for Stagehand/Playwright.'; exit 1; }

python -m pip install --upgrade pip
python -m pip install 'skyvern[all]==1.0.48'
npm install --save '@browserbasehq/stagehand@4.0.2' 'playwright@1.62.1'
npx playwright install chromium

echo 'Installed. Next: skyvern quickstart'
