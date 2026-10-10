#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";

const candidate = path.resolve(process.argv[2] || "");
const reportPath = path.resolve(process.argv[3] || "");
if (!process.argv[2] || !process.argv[3]) {
  console.error("usage: node louksna_zd_v03_playwright_ui_e2e.mjs <candidate-root> <report-path>");
  process.exit(2);
}
const screenshotPath = path.join(path.dirname(reportPath), "CP-07-playwright-ui-e2e.png");
const log = [];
let server;
let browser;
const started = new Date().toISOString();
const checks = [];
const pageErrors = [];
const requireFromCandidate = createRequire(path.join(candidate, "package.json"));

function record(id, passed, detail) {
  checks.push({ id, status: passed ? "PASS" : "FAIL", detail });
  if (!passed) throw new Error("CHECK_FAILED:" + id + ":" + detail);
}
function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }
async function waitForServer(url, timeoutMs = 45000) {
  const end = Date.now() + timeoutMs;
  let lastError = "not attempted";
  while (Date.now() < end) {
    if (server?.exitCode !== null && server?.exitCode !== undefined) {
      throw new Error("VITE_EXITED_EARLY:" + server.exitCode + ":" + log.join("").slice(-5000));
    }
    try {
      const response = await fetch(url);
      if (response.ok) return;
      lastError = "HTTP_" + response.status;
    } catch (error) {
      lastError = String(error);
    }
    await sleep(500);
  }
  throw new Error("VITE_READY_TIMEOUT:" + lastError + ":" + log.join("").slice(-5000));
}

async function main() {
  const { chromium } = requireFromCandidate("playwright");
  const pkg = JSON.parse(await fs.readFile(path.join(candidate, "package.json"), "utf8"));
  record("candidate_package_present", Boolean(pkg.name && pkg.scripts?.dev), "package.json and dev script are present");

  server = spawn("npm", ["run", "dev", "--", "--host", "127.0.0.1"], {
    cwd: candidate,
    env: { ...process.env, CI: "1" },
    stdio: ["ignore", "pipe", "pipe"]
  });
  server.stdout.on("data", chunk => log.push(String(chunk)));
  server.stderr.on("data", chunk => log.push(String(chunk)));
  await waitForServer("http://127.0.0.1:1420");

  browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  await context.addInitScript((seed) => {
    const key = "__louksna_cp07_ipc_fixture";
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem(key) || "null"); } catch {}
    const state = {
      settings: saved?.settings || seed.settings,
      chats: saved?.chats || [],
      calls: [],
      evidence: [{ id: 1, utc: "2026-10-10T00:00:00Z", operation: "UI_E2E_FIXTURE", status: "PASS", detail: "Explicit browser-only IPC test double; not native runtime evidence." }]
    };
    const persist = () => localStorage.setItem(key, JSON.stringify({ settings: state.settings, chats: state.chats }));
    window.__louksnaTestState = state;
    window.__TAURI_INTERNALS__ = {
      invoke: async (command, args = {}) => {
        state.calls.push({ command, args });
        switch (command) {
          case "get_settings": return state.settings;
          case "save_settings": state.settings = args.settings; persist(); return null;
          case "evidence_recent": return state.evidence;
          case "chat_history": return state.chats;
          case "chat_send": {
            const message = String(args.message || "");
            state.chats.push({ id: state.chats.length + 1, utc: new Date().toISOString(), role: "user", content: message, transport: "local-test-double" });
            state.chats.push({ id: state.chats.length + 1, utc: new Date().toISOString(), role: "louksna", content: "Respuesta de prueba local.", transport: "local-test-double" });
            persist();
            return "Respuesta de prueba local.";
          }
          case "github_connection": return { connected: false, login: "", name: "" };
          case "github_repositories": return [{ full_name: "Plomillo/luna-linux-bridge", private: false, default_branch: "main", updated_at: "2026-10-10T00:00:00Z", open_issues_count: 0 }];
          case "github_pull_requests": return [];
          case "store_github_token": return null;
          case "remove_github_token": return null;
          default: throw new Error("UNEXPECTED_TAURI_COMMAND:" + command);
        }
      }
    };
  }, {
    settings: { offline_mode: false, preferred_repo: "", github_owner_filter: "", remote_chat_bridge: "" }
  });

  const page = await context.newPage();
  page.on("pageerror", error => pageErrors.push(String(error)));
  await page.goto("http://127.0.0.1:1420", { waitUntil: "networkidle", timeout: 30000 });
  await page.getByRole("heading", { name: "Centro de mando" }).waitFor({ timeout: 10000 });

  const navButtons = page.getByRole("navigation").getByRole("button");
  record("six_canonical_sections", await navButtons.count() === 6, "The six navigation sections render.");
  record("louksna_identity_visible", await page.getByText("LOUKSNA", { exact: true }).count() >= 1, "LOUKSNA identity is present.");

  await navButtons.filter({ hasText: "Repositorios" }).click();
  await page.getByRole("button", { name: /Actualizar/ }).click();
  await page.getByText("Plomillo/luna-linux-bridge", { exact: true }).waitFor({ timeout: 5000 });
  record("repository_view_uses_fixture", true, "Repository UI renders data returned by the explicit IPC test double.");
  await page.getByRole("button", { name: /Plomillo\/luna-linux-bridge/ }).click();

  await navButtons.filter({ hasText: "Pull Requests" }).click();
  await page.getByRole("button", { name: /Actualizar/ }).click();
  await page.getByText(/PR abiertos leidos de Plomillo\/luna-linux-bridge/).waitFor({ timeout: 5000 });
  record("pull_request_refresh", true, "Pull-request action completes through the IPC test double.");

  await navButtons.filter({ hasText: "Chat \/ Llamada" }).click();
  await page.getByPlaceholder("Escribe a LOUKSNA...").fill("Prueba E2E gobernada");
  await page.getByRole("button", { name: "Enviar" }).click();
  await page.getByText("Prueba E2E gobernada", { exact: true }).waitFor({ timeout: 5000 });
  record("chat_send_and_history", true, "Chat message and response render from test-double history.");

  await navButtons.filter({ hasText: "Configuracion" }).click();
  const offline = page.getByLabel(/Modo offline/);
  await offline.check();
  await page.getByLabel("Repositorio preferido").fill("Plomillo/luna-linux-bridge");
  await page.getByRole("button", { name: "Guardar configuracion" }).click();
  await page.getByText("Configuracion persistida localmente.").waitFor({ timeout: 5000 });
  record("settings_save", true, "Settings-save command is invoked and UI acknowledges the test-double response.");

  const calls = await page.evaluate(() => window.__louksnaTestState.calls.map(x => x.command));
  record("ipc_commands_observed", ["get_settings", "evidence_recent", "chat_history", "github_repositories", "github_pull_requests", "chat_send", "save_settings"].every(x => calls.includes(x)), "Required UI commands were observed: " + calls.join(","));
  record("no_page_errors", pageErrors.length === 0, pageErrors.join(" | ") || "No uncaught browser page errors.");

  await page.screenshot({ path: screenshotPath, fullPage: true });
  await page.reload({ waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Configuracion" }).waitFor({ timeout: 10000 });
  record("fixture_reload_state", await page.getByLabel(/Modo offline/).isChecked(), "Fixture-backed setting survives reload; this is not proof of native SQLite persistence.");

  const report = {
    schema: "louksna.zd.v03.playwright-ui-e2e.v1",
    stage_id: "07",
    checkpoint_id: "CP-07",
    started_at_utc: started,
    finished_at_utc: new Date().toISOString(),
    repository: process.env.GITHUB_REPOSITORY || "Plomillo/luna-linux-bridge",
    commit_sha: process.env.CANDIDATE_SHA || process.env.GITHUB_SHA || null,
    run_id: process.env.GITHUB_RUN_ID || null,
    frontend_browser_e2e_executed: true,
    native_tauri_runtime_tested: false,
    tauri_ipc_mode: "EXPLICIT_BROWSER_TEST_DOUBLE",
    voice_e2e_executed: false,
    status: "PASS_WITH_SCOPE_LIMITS",
    checks,
    page_errors: pageErrors,
    screenshot: screenshotPath,
    limitations: [
      "The UI was exercised in Chromium with an explicit Tauri IPC test double; this is not a native Tauri process test.",
      "Fixture-backed localStorage across reload is not evidence of SQLite persistence across native application restart.",
      "GitHub responses are fixtures, not live authenticated GitHub API responses.",
      "Voice capture, transport, and end-to-end response are not tested; the voice gate remains OPEN and G23/G24 remain blocked."
    ]
  };
  await fs.mkdir(path.dirname(reportPath), { recursive: true });
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify(report, null, 2));
}

try {
  await main();
} catch (error) {
  const report = {
    schema: "louksna.zd.v03.playwright-ui-e2e.v1",
    stage_id: "07",
    checkpoint_id: "CP-07",
    started_at_utc: started,
    finished_at_utc: new Date().toISOString(),
    repository: process.env.GITHUB_REPOSITORY || "Plomillo/luna-linux-bridge",
    commit_sha: process.env.CANDIDATE_SHA || process.env.GITHUB_SHA || null,
    run_id: process.env.GITHUB_RUN_ID || null,
    frontend_browser_e2e_executed: true,
    native_tauri_runtime_tested: false,
    tauri_ipc_mode: "EXPLICIT_BROWSER_TEST_DOUBLE",
    voice_e2e_executed: false,
    status: "FAIL",
    checks,
    error: String(error),
    server_log_tail: log.join("").slice(-10000),
    page_errors: pageErrors,
    limitations: ["Native Tauri runtime and voice E2E are not tested by this harness."]
  };
  await fs.mkdir(path.dirname(reportPath), { recursive: true }).catch(() => {});
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2) + "\n").catch(() => {});
  console.error(JSON.stringify(report, null, 2));
  process.exitCode = 1;
} finally {
  if (browser) await browser.close().catch(() => {});
  if (server && server.exitCode === null) {
    server.kill("SIGTERM");
    await Promise.race([new Promise(resolve => server.once("exit", resolve)), sleep(3000)]);
    if (server.exitCode === null) server.kill("SIGKILL");
  }
}
