#!/usr/bin/env node
"use strict";

/*
 * Brújula giroscópica — Lunita v1.8 browser instrument.
 * Uses the pinned local Playwright and Chrome for Testing payload.
 * No browser binary or package is downloaded at runtime.
 */
const path = require("node:path");
const { chromium } = require("playwright");

const CHROME = path.join(__dirname, "chrome", "chrome");

async function main() {
  const target = process.argv[2] || "about:blank";
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
    args: ["--disable-dev-shm-usage"]
  });

  try {
    const page = await browser.newPage();
    page.setDefaultNavigationTimeout(60000);
    await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60000 });
    const result = await page.evaluate(() => ({
      title: document.title || "",
      url: location.href,
      text: (document.body?.innerText || "").slice(0, 12000)
    }));
    process.stdout.write("LUNITA_BRUJULA_OK\n");
    process.stdout.write(JSON.stringify(result) + "\n");
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write("LUNITA_BRUJULA_ERROR: " + (error?.stack || error) + "\n");
  process.exitCode = 1;
});
