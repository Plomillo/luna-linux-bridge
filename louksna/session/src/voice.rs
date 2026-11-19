use crate::error::{err, Result};
use serde_json::Value;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

pub const REQUIRED_SPEAKER: &str = "1";
pub const REQUIRED_MODEL_FILE: &str = "es_ES-sharvard-medium.onnx";

pub fn female_speaker_id(model_json: &str) -> Result<u32> {
    let v: Value = serde_json::from_str(model_json)?;
    let map = v.get("speaker_id_map").ok_or_else(|| err("SPEAKER_MAP_MISSING"))?;
    let id = map.get("F").and_then(|x| x.as_u64()).ok_or_else(|| err("FEMALE_SPEAKER_MISSING"))?;
    if id != 1 {
        return Err(err(format!("FEMALE_SPEAKER_NOT_1:{id}")));
    }
    let lang = v
        .pointer("/language/code")
        .and_then(|x| x.as_str())
        .unwrap_or("");
    if lang != "es_ES" {
        return Err(err(format!("MODEL_LANGUAGE_NOT_ES_ES:{lang}")));
    }
    Ok(1)
}

#[derive(Debug, Clone)]
pub struct PiperInvocation {
    pub program: String,
    pub args: Vec<String>,
}

pub fn piper_invocation(program: &str, model: &str, output: &str) -> PiperInvocation {
    PiperInvocation {
        program: program.to_string(),
        args: vec![
            "--model".into(),
            model.into(),
            "--speaker".into(),
            REQUIRED_SPEAKER.into(),
            "--output_file".into(),
            output.into(),
        ],
    }
}

pub fn assert_speaker_locked(inv: &PiperInvocation) -> Result<()> {
    let pos = inv.args.iter().position(|a| a == "--speaker").ok_or_else(|| err("SPEAKER_FLAG_MISSING"))?;
    let value = inv.args.get(pos + 1).ok_or_else(|| err("SPEAKER_VALUE_MISSING"))?;
    if value != REQUIRED_SPEAKER {
        return Err(err("SPEAKER_NOT_1"));
    }
    if !inv.args.iter().any(|a| a.ends_with(REQUIRED_MODEL_FILE)) {
        return Err(err("MODEL_NOT_SHARVARD_MEDIUM"));
    }
    Ok(())
}

pub fn speak(program: &str, model: &Path, text: &str, output: &Path) -> Result<()> {
    if text.trim().is_empty() {
        return Err(err("EMPTY_SPEECH_TEXT"));
    }
    if !model.is_file() {
        return Err(err("PIPER_MODEL_ABSENT"));
    }
    let json_path = {
        let s = format!("{}.json", model.display());
        PathBuf::from(s)
    };
    if json_path.is_file() {
        let raw = std::fs::read_to_string(json_path)?;
        female_speaker_id(&raw)?;
    } else {
        return Err(err("PIPER_MODEL_JSON_ABSENT"));
    }
    let inv = piper_invocation(program, &model.display().to_string(), &output.display().to_string());
    assert_speaker_locked(&inv)?;
    if !Path::new(program).is_file() && which_missing(program) {
        return Err(err("PIPER_RUNTIME_ABSENT"));
    }
    if let Some(parent) = output.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut child = Command::new(&inv.program)
        .args(&inv.args)
        .env("PYTHONNOUSERSITE", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()?;
    if let Some(mut stdin) = child.stdin.take() {
        stdin.write_all(text.as_bytes())?;
        stdin.write_all(b"\n")?;
    }
    let out = child.wait_with_output()?;
    if !out.status.success() {
        let stderr = String::from_utf8_lossy(&out.stderr);
        return Err(err(format!("PIPER_EXIT:{}", stderr.chars().take(400).collect::<String>())));
    }
    let wav = std::fs::read(output)?;
    if wav.len() < 44 || &wav[0..4] != b"RIFF" {
        return Err(err("PIPER_WAV_INVALID"));
    }
    Ok(())
}

fn which_missing(program: &str) -> bool {
    Command::new(program).arg("--help").stdout(Stdio::null()).stderr(Stdio::null()).status().is_err()
}

pub fn whisper_invocation(program: &str, model: &str, wav: &str) -> (String, Vec<String>) {
    (
        program.to_string(),
        vec![
            "-m".into(),
            model.into(),
            "-f".into(),
            wav.into(),
            "-l".into(),
            "es".into(),
            "--no-timestamps".into(),
        ],
    )
}

pub fn reject_empty_audio(bytes: &[u8]) -> Result<()> {
    if bytes.len() < 44 || &bytes[0..4] != b"RIFF" {
        return Err(err("AUDIO_NOT_WAV"));
    }
    let n = bytes.len() - 44;
    if n == 0 {
        return Err(err("AUDIO_EMPTY"));
    }
    Ok(())
}

pub fn transcribe(program: &str, model: &Path, wav: &Path) -> Result<String> {
    if !model.is_file() {
        return Err(err("WHISPER_MODEL_ABSENT"));
    }
    let bytes = std::fs::read(wav)?;
    reject_empty_audio(&bytes)?;
    if !Path::new(program).is_file() && which_missing(program) {
        return Err(err("WHISPER_RUNTIME_ABSENT"));
    }
    let (bin, args) = whisper_invocation(program, &model.display().to_string(), &wav.display().to_string());
    let out = Command::new(bin).args(args).output()?;
    if !out.status.success() {
        let stderr = String::from_utf8_lossy(&out.stderr);
        return Err(err(format!("WHISPER_EXIT:{}", stderr.chars().take(400).collect::<String>())));
    }
    let text = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if text.is_empty() {
        return Err(err("WHISPER_EMPTY_TRANSCRIPT"));
    }
    Ok(text)
}
