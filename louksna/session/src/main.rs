use louksna_session::error::Result;
use louksna_session::g23;
use louksna_session::http;
use louksna_session::runtime::App;
use std::env;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};

fn arg_value(args: &[String], name: &str) -> Option<String> {
    args.iter().position(|a| a == name).and_then(|i| args.get(i + 1).cloned())
}

fn state_dir(args: &[String]) -> PathBuf {
    arg_value(args, "--state").map(PathBuf::from).unwrap_or_else(|| {
        let home = env::var("HOME").unwrap_or_else(|_| "/tmp".into());
        PathBuf::from(home).join(".local/share/louksna")
    })
}

fn output_has_secret(text: &str) -> bool {
    const MARKS: &[&str] = &["ghu_", "ghs_", "ghp_", "gho_", "github_pat_", "xai-"];
    MARKS.iter().any(|mark| text.contains(mark))
}

fn locate_mra_suite() -> Result<PathBuf> {
    if let Ok(raw) = env::var("LOUKSNA_MRA_SUITE") {
        let path = PathBuf::from(raw);
        if path.join("suite.py").is_file() {
            return Ok(path);
        }
        return Err(louksna_session::error::err("MRA_SUITE_ENV_INVALID"));
    }
    if let Ok(exe) = env::current_exe() {
        if let Some(bin_dir) = exe.parent() {
            let bundled = bin_dir.join("../lib/louksna/mra_suite");
            if bundled.join("suite.py").is_file() {
                return Ok(bundled);
            }
        }
    }
    let compiled = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../mra_suite");
    if compiled.join("suite.py").is_file() {
        return Ok(compiled);
    }
    Err(louksna_session::error::err("MRA_SUITE_ABSENT"))
}

fn locate_python() -> Result<PathBuf> {
    if let Ok(raw) = env::var("LOUKSNA_PYTHON") {
        let path = PathBuf::from(raw);
        if path.is_file() {
            return Ok(path);
        }
        return Err(louksna_session::error::err("PYTHON_ENV_INVALID"));
    }
    if let Ok(exe) = env::current_exe() {
        if let Some(bin_dir) = exe.parent() {
            let bundled = bin_dir.join("../lib/louksna/python/bin/python3");
            if bundled.is_file() {
                return Ok(bundled);
            }
        }
    }
    Ok(PathBuf::from("python3"))
}

fn require_status(row: &serde_json::Value) -> Result<()> {
    let status = row["status"].as_str().unwrap_or("");
    if !matches!(status, "HISTORICAL_PRESERVED" | "NOT_PRESENT" | "PASS_FUNCTIONAL" | "BLOCKED") {
        return Err(louksna_session::error::err("MRA856_STATUS"));
    }
    let certification = row["certification"].as_str().unwrap_or("");
    if !matches!(certification, "NOT_CERTIFIED" | "CERTIFIED") || row["weight_training"] != "NOT_AUTHORIZED" || row["consciousness"] != "NOT_CLAIMED" {
        return Err(louksna_session::error::err("MRA856_FORBIDDEN_CLAIM"));
    }
    let historical_ok = status == "HISTORICAL_PRESERVED"
        && row["independent_validation"] == "INDEPENDENTLY_VALIDATED";
    if certification == "CERTIFIED" && status != "PASS_FUNCTIONAL" && !historical_ok {
        return Err(louksna_session::error::err("MRA856_CERTIFIED_NON_PASS"));
    }
    if status == "BLOCKED" && row["unlock"].as_str().unwrap_or("").is_empty() {
        return Err(louksna_session::error::err("MRA856_BLOCKED_WITHOUT_UNLOCK"));
    }
    Ok(())
}

fn validate_mra856(report: &serde_json::Value, cases: &serde_json::Value) -> Result<()> {
    if report["count"] != 856 || report["unique"] != true || report["historical_failed"] != 0 {
        return Err(louksna_session::error::err("MRA856_SUMMARY"));
    }
    if report["bad"].as_array().map(|rows| !rows.is_empty()).unwrap_or(true) {
        return Err(louksna_session::error::err("MRA856_BAD"));
    }
    if report["product_platform"] != "NOT_CERTIFIED" || report["weight_training"] != "NOT_AUTHORIZED" || report["consciousness"] != "NOT_CLAIMED" {
        return Err(louksna_session::error::err("MRA856_FORBIDDEN_CLAIM"));
    }
    let counts = report["counts"].as_object().ok_or_else(|| louksna_session::error::err("MRA856_COUNTS"))?;
    let sum: u64 = counts.values().filter_map(|value| value.as_u64()).sum();
    if sum != 856 {
        return Err(louksna_session::error::err("MRA856_COUNT_SUM"));
    }
    let rows = cases.as_array().ok_or_else(|| louksna_session::error::err("MRA856_CASES"))?;
    if rows.len() != 856 {
        return Err(louksna_session::error::err("MRA856_CASES"));
    }
    for (index, row) in rows.iter().enumerate() {
        if row["n"] != index as u64 + 1 {
            return Err(louksna_session::error::err("MRA856_SEQUENCE"));
        }
        require_status(row)?;
    }
    Ok(())
}

fn mra856(args: &[String], state: &Path) -> Result<ExitCode> {
    if env::var_os("LOUKSNA_MRA856_CHILD").is_some() {
        return Err(louksna_session::error::err("MRA856_RECURSION"));
    }
    let suite = locate_mra_suite()?;
    let python = locate_python()?;
    let out = arg_value(args, "--out").map(PathBuf::from).unwrap_or_else(|| state.join("mra-856"));
    std::fs::create_dir_all(&out)?;
    let proc = Command::new(&python)
        .arg(suite.join("suite.py"))
        .arg(&out)
        .current_dir(&suite)
        .env("LOUKSNA_MRA856_CHILD", "1")
        .env("LOUKSNA_SESSION_BIN", env::current_exe()?)
        .env_remove("XAI_API_KEY")
        .env_remove("LOUKSNA_XAI_API_KEY")
        .output()?;
    let stdout = String::from_utf8_lossy(&proc.stdout);
    let stderr = String::from_utf8_lossy(&proc.stderr);
    if output_has_secret(&stdout) || output_has_secret(&stderr) {
        return Err(louksna_session::error::err("MRA856_SECRET_IN_OUTPUT"));
    }
    if !proc.status.success() {
        eprint!("{stderr}");
        print!("{stdout}");
        return Ok(ExitCode::from(1));
    }
    let report: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(out.join("report.json"))?)?;
    let cases: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(out.join("cases.json"))?)?;
    validate_mra856(&report, &cases)?;
    print!("{stdout}");
    Ok(ExitCode::SUCCESS)
}

fn run() -> Result<ExitCode> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.iter().any(|a| a == "--selftest") {
        let report = louksna_session::selftest()?;
        println!("{}", serde_json::to_string_pretty(&report)?);
        return Ok(if report["ok"] == true { ExitCode::SUCCESS } else { ExitCode::from(1) });
    }
    let state = state_dir(&args);
    if args.iter().any(|a| a == "--mra-856") {
        return mra856(&args, &state);
    }
    if args.iter().any(|a| a == "--mra") {
        let report = louksna_session::mra::run_suite(&state)?;
        println!("{}", serde_json::to_string_pretty(&report)?);
        return Ok(if louksna_session::mra::suite_exit_ok(&report) { ExitCode::SUCCESS } else { ExitCode::from(1) });
    }
    if args.iter().any(|a| a == "--mra-oracle") {
        let path = arg_value(&args, "--report").ok_or_else(|| louksna_session::error::err("MRA_REPORT_REQUIRED"))?;
        let submitted: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(path)?)?;
        let verdict = louksna_session::mra::oracle_verify(&submitted)?;
        println!("{}", serde_json::to_string_pretty(&verdict)?);
        return Ok(if verdict["verdict"] == "GRANTED" { ExitCode::SUCCESS } else { ExitCode::from(1) });
    }
    if args.iter().any(|a| a == "--g23") {
        let app = App::open(&state)?;
        let verdict = g23::validate(&app.store)?;
        let path = state.join("g23-verdict.json");
        g23::write_verdict(&path, &verdict)?;
        println!("{}", serde_json::to_string_pretty(&verdict)?);
        return Ok(if verdict["verdict"] == "PASS" { ExitCode::SUCCESS } else { ExitCode::from(1) });
    }
    if args.iter().any(|a| a == "--g24") {
        let app = App::open(&state)?;
        let subject = arg_value(&args, "--subject").unwrap_or_else(|| "product".into());
        let verdict = g23::certify_g24(&app.store, &state.join("g23-verdict.json"), &subject)?;
        println!("{}", serde_json::to_string_pretty(&verdict)?);
        return Ok(ExitCode::SUCCESS);
    }
    if args.iter().any(|a| a == "--speak") {
        let text = arg_value(&args, "--speak").ok_or_else(|| louksna_session::error::err("SPEAK_TEXT_REQUIRED"))?;
        let app = App::open(&state)?;
        let path = app.speak(&text)?;
        println!("{}", path.display());
        return Ok(ExitCode::SUCCESS);
    }
    if args.iter().any(|a| a == "--transcribe") {
        let wav = arg_value(&args, "--transcribe").ok_or_else(|| louksna_session::error::err("WAV_REQUIRED"))?;
        let app = App::open(&state)?;
        let copied = state.join("attachments").join("in.wav");
        std::fs::create_dir_all(state.join("attachments"))?;
        std::fs::copy(&wav, &copied)?;
        let text = app.transcribe_wav(&copied)?;
        println!("{text}");
        return Ok(ExitCode::SUCCESS);
    }
    if args.iter().any(|a| a == "--serve") {
        let bind = arg_value(&args, "--bind").unwrap_or_else(|| "127.0.0.1:47321".into());
        http::serve(&state, &bind)?;
        return Ok(ExitCode::SUCCESS);
    }
    eprintln!("usage: louksna-session --selftest | --mra | --mra-856 | --serve [--bind 127.0.0.1:47321] [--state DIR] | --g23 | --g24");
    Ok(ExitCode::from(2))
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => code,
        Err(e) => {
            eprintln!("LOUKSNA_FAIL:{e}");
            ExitCode::from(1)
        }
    }
}
