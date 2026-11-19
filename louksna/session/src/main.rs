use louksna_session::error::Result;
use louksna_session::g23;
use louksna_session::http;
use louksna_session::runtime::App;
use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

fn arg_value(args: &[String], name: &str) -> Option<String> {
    args.iter().position(|a| a == name).and_then(|i| args.get(i + 1).cloned())
}

fn state_dir(args: &[String]) -> PathBuf {
    arg_value(args, "--state").map(PathBuf::from).unwrap_or_else(|| {
        let home = env::var("HOME").unwrap_or_else(|_| "/tmp".into());
        PathBuf::from(home).join(".local/share/louksna")
    })
}

fn run() -> Result<ExitCode> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.iter().any(|a| a == "--selftest") {
        let report = louksna_session::selftest()?;
        println!("{}", serde_json::to_string_pretty(&report)?);
        return Ok(if report["ok"] == true { ExitCode::SUCCESS } else { ExitCode::from(1) });
    }
    let state = state_dir(&args);
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
    eprintln!("usage: louksna-session --selftest | --serve [--bind 127.0.0.1:47321] [--state DIR] | --g23 | --g24");
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
