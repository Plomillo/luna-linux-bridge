#!/usr/bin/env node
/**
 * CP-07 browser E2E for the generated Louksna frontend.
 * The Tauri IPC backend is an explicit test double; this verifies real browser/UI
 * behavior only and MUST NOT be interpreted as native-runtime, voice, or API proof.
 */
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { createRequire } from "node:module";

const candidate = path.resolve(process.argv[2] || "");
const reportPath = path.resolve(process.argv[3] || "evidence/zona-directiva-v03/CP-07-playwright-ui-e2e.json");
const started = new Date().toISOString();
fs.mkdirSync(path.dirname(reportPath), { recursive: true });
const bootstrapReport = {
  schema: "louksna.zd.v03.playwright-ui-e2e.v1",
  stage_id: "07", checkpoint_id: "CP-07",
  started_at_utc: started, finished_at_utc: null,
  repository: process.env.GITHUB_REPOSITORY || null,
  commit_sha: process.env.GITHUB_SHA || null,
  run_id: process.env.GITHUB_RUN_ID || null,
  frontend_browser_e2e_executed: false,
  native_tauri_runtime_tested: false, voice_e2e_executed: false,
  status: "STARTED", failures: ["e2e_not_completed"]
};
fs.writeFileSync(reportPath, JSON.stringify(bootstrapReport, null, 2) + "\n");
console.log("CP-07 startup: candidate=" + candidate);
const baseURL = "http://127.0.0.1:4173";
const evidenceDir = path.dirname(reportPath);
const failures = [];
const assertions = [];
let server;
let browser;
let chromium;
const check = (name, condition, detail = "") => {
  assertions.push({ name, status: condition ? "PASS" : "FAIL", detail });
  if (!condition) failures.push(name);
};
try {
  if (!fs.existsSync(path.join(candidate, "package.json"))) throw new Error("candidate package.json missing");
  console.log("CP-07 startup: resolving Playwright from candidate package");
  const requireFromCandidate = createRequire(path.join(candidate, "package.json"));
  ({ chromium } = requireFromCandidate("playwright"));
  console.log("CP-07 startup: Playwright module loaded");
  console.log("CP-07 E2E: starting bounded Vite server");
  // Do not keep child stdout/stderr pipes open: npm/Vite can leave inherited
  // handles alive after the E2E report is written, causing the CI step to hang.
  server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1", "--port", "4173", "--strictPort"], {
    cwd: candidate, stdio: "ignore", detached: true, env: { ...process.env, CI: "true" }
  });
  let ready = false;
  for (let i = 0; i < 30; i++) {
    if (server.exitCode !== null) throw new Error("Vite exited before ready (exit code " + server.exitCode + ")");
    try { const r = await fetch(baseURL); if (r.ok) { ready = true; break; } } catch {}
    await delay(1000);
  }
  if (!ready) throw new Error("Vite readiness timeout at " + baseURL);
  console.log("CP-07 E2E: Vite ready; launching pinned Chromium");

  // Bound browser startup independently; CI must produce failure evidence rather
  // than hanging until the outer workflow timeout.
  browser = await chromium.launch({
    headless: true,
    timeout: 20000,
    args: ["--no-sandbox", "--disable-dev-shm-usage"]
  });
  console.log("CP-07 E2E: Chromium launched; initializing page");
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  console.log("CP-07 E2E: page initialized; beginning UI assertions");
  page.setDefaultTimeout(8000);
  page.setDefaultNavigationTimeout(15000);
  const pageErrors = [];
  page.on("pageerror", e => pageErrors.push(String(e)));
  await page.addInitScript(() => {
    const state = {
      settings: { offline_mode: false, preferred_repo: "", github_owner_filter: "", remote_chat_bridge: "" },
      evidence: [{ id: 1, utc: "2026-10-09T00:00:00Z", operation: "E2E_TEST", status: "PASS", detail: "Explicit Playwright IPC test double" }],
      chats: [],
      calls: []
    };
    const repo = { full_name: "Plomillo/luna-linux-bridge", private: false, default_branch: "main", updated_at: "2026-10-09T00:00:00Z", open_issues_count: 0 };
    window.__LOUKSNA_E2E_TEST_DOUBLE__ = state;
    window.__TAURI_INTERNALS__ = {
      invoke: async (command, args = {}) => {
        state.calls.push({ command, args });
        switch (command) {
          case "get_settings": return state.settings;
          case "save_settings": state.settings = args.settings; state.evidence.push({ id: state.evidence.length + 1, utc: new Date().toISOString(), operation: "SETTINGS_SAVE", status: "PASS", detail: "test double" }); return null;
          case "evidence_recent": return state.evidence;
          case "chat_history": return state.chats;
          case "github_connection": return { connected: true, login: "e2e-test", name: "E2E test double" };
          case "github_repositories": return [repo];
          case "github_pull_requests": return [{ number: 54, title: "Governance automation E2E fixture", state: "open", draft: true, updated_at: "2026-10-09T00:00:00Z", html_url: "https://github.com/Plomillo/luna-linux-bridge/pull/54" }];
          case "chat_send": state.chats.push({ id: state.chats.length + 1, utc: new Date().toISOString(), role: "user", content: args.message, transport: "LOCAL_E2E_TEST_DOUBLE" }); return "accepted";
          case "store_github_token": return null;
          case "remove_github_token": return null;
          default: throw new Error("Unimplemented test-double command: " + command);
        }
      }
    };
  });

  console.log("CP-07 E2E: opening local candidate");
  await page.goto(baseURL, { waitUntil: "domcontentloaded", timeout: 15000 });
  await page.getByRole("heading", { name: "Centro de mando" }).waitFor();
  console.log("CP-07 E2E: dashboard rendered");
  check("dashboard_renders", await page.getByText("Estado real, no decorativo.").isVisible());
  for (const label of ["Repositorios", "Pull Requests", "Evidencia", "Chat / Llamada", "Configuracion"]) {
    console.log("CP-07 E2E: navigating to " + label);
    await page.getByRole("button", { name: label, exact: true }).click();
    const heading = await page.locator("header h1").innerText();
    check("navigation_" + label.toLowerCase().replace(/[^a-z0-9]+/g, "_"), heading === label, "Rendered heading: " + heading);
  }

  console.log("CP-07 E2E: verifying repository list");
  await page.getByRole("button", { name: "Repositorios", exact: true }).click();
  await page.getByRole("button", { name: "Actualizar", exact: true }).click();
  const repositoryRow = page.getByText("Plomillo/luna-linux-bridge", { exact: true });
  await repositoryRow.waitFor();
  check("repository_list_interaction", await repositoryRow.isVisible());
  await repositoryRow.click(); // select the fixture repo before asking the PR endpoint


  console.log("CP-07 E2E: verifying pull request list");
  await page.getByRole("button", { name: "Pull Requests", exact: true }).click();
  await page.getByRole("button", { name: "Actualizar", exact: true }).click();
  await page.getByText("#54 · Governance automation E2E fixture").waitFor();
  check("pull_request_list_interaction", await page.getByText("#54 · Governance automation E2E fixture").isVisible());

  console.log("CP-07 E2E: verifying chat and disabled voice control");
  await page.getByRole("button", { name: "Chat / Llamada", exact: true }).click();
  const mic = page.getByRole("button", { name: "Microfono — gate abierto" });
  check("microphone_remains_disabled", await mic.isDisabled(), "Voice is intentionally not represented as active");
  await page.getByPlaceholder("Escribe a LOUKSNA...").fill("CP-07 browser E2E");
  await page.getByRole("button", { name: "Enviar", exact: true }).click();
  await page.getByText("CP-07 browser E2E", { exact: true }).waitFor();
  check("chat_interaction_with_explicit_test_double", await page.getByText("CP-07 browser E2E", { exact: true }).isVisible());

  console.log("CP-07 E2E: verifying evidence ledger view");
  await page.getByRole("button", { name: "Evidencia", exact: true }).click();
  await page.getByText("E2E_TEST", { exact: true }).waitFor();
  check("evidence_view_renders", await page.getByText("E2E_TEST", { exact: true }).isVisible());
  await page.screenshot({ path: path.join(evidenceDir, "CP-07-playwright-ui-e2e.png"), fullPage: true });
  check("no_uncaught_page_errors", pageErrors.length === 0, pageErrors.join(" | "));
  const version = "1.55.0"; // pinned by the CP-07 workflow bootstrap
  const report = {
    schema: "louksna.zd.v03.playwright-ui-e2e.v1",
    stage_id: "07",
    checkpoint_id: "CP-07",
    started_at_utc: started,
    finished_at_utc: new Date().toISOString(),
    repository: process.env.GITHUB_REPOSITORY || null,
    commit_sha: process.env.GITHUB_SHA || null,
    run_id: process.env.GITHUB_RUN_ID || null,
    browser: "Chromium headless",
    playwright_version: version,
    candidate_path: candidate,
    frontend_browser_e2e_executed: true,
    native_tauri_runtime_tested: false,
    real_github_api_tested_by_this_harness: false,
    voice_e2e_executed: false,
    backend_mode: "EXPLICIT_TAURI_IPC_TEST_DOUBLE",
    assertions,
    page_errors: pageErrors,
    status: failures.length ? "FAIL" : "PASS_WITH_SCOPE_LIMITS",
    failures,
    limitations: [
      "This proves browser-level frontend navigation and interactions against a declared IPC test double.",
      "It does not prove the native Tauri process, SQLite persistence across restart, real GitHub credentials/API, microphone capture, audio transport, remote voice response, or Debian 13 KDE installation/rollback."
    ]
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify(report, null, 2));
  if (failures.length) process.exitCode = 1;
} catch (error) {
  const report = {
    schema: "louksna.zd.v03.playwright-ui-e2e.v1",
    stage_id: "07", checkpoint_id: "CP-07",
    started_at_utc: started, finished_at_utc: new Date().toISOString(),
    repository: process.env.GITHUB_REPOSITORY || null,
    commit_sha: process.env.GITHUB_SHA || null,
    run_id: process.env.GITHUB_RUN_ID || null,
    frontend_browser_e2e_executed: false,
    native_tauri_runtime_tested: false,
    voice_e2e_executed: false,
    status: "FAIL",
    error: String(error),
    assertions,
    failures
  };
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
  console.error(error);
  process.exitCode = 1;
} finally {
  // Browser shutdown is not part of the test assertion surface. Bound it so the
  // completed report cannot be held hostage by a stuck Chromium close handshake.
  if (browser) {
    await Promise.race([browser.close().catch(() => {}), delay(1500)]);
  }
  if (server) {
    // npm may leave Vite as a child; terminate the detached process group, not
    // only the npm parent. All cleanup waits are bounded.
    try { process.kill(-server.pid, "SIGTERM"); } catch { server.kill("SIGTERM"); }
    await Promise.race([new Promise(resolve => server.once("exit", resolve)), delay(750)]);
    try { process.kill(-server.pid, "SIGKILL"); } catch { if (server.exitCode === null) server.kill("SIGKILL"); }
    server.stdout?.destroy();
    server.stderr?.destroy();
    server.unref();
  }
}
