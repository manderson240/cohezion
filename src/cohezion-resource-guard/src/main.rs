//! Resident RAM + ctx_size guard.
//!
//! WHY THIS EXISTS IN RUST (measured 2026-07-26): the Python equivalent costs **684 MB RSS** just to
//! import, because reaching `oom_guard` pulls in the whole `cohezion` package. A service whose only
//! job is defending a 16 GB available-RAM floor was consuming 4.3% of that floor to exist. Its actual
//! work is: read /proc/meminfo, parse integers, make localhost HTTP GETs, log a line. That is not a
//! Python-shaped job.
//!
//! ZERO DEPENDENCIES BY DESIGN. No serde, no reqwest, no tokio. Three reasons:
//!   1. A guard must not become part of the problem it watches — every crate is resident bytes.
//!   2. It builds with no crates.io access, so it cannot be blocked by a sandboxed network.
//!   3. Fewer moving parts to rot. (This week found 5 systemd units pointing at things that no
//!      longer existed; a dependency-free binary has one referent: itself.)
//!
//! SIGTERM is deliberately unhandled: the default disposition terminates the process, which is
//! correct for a stateless poller. Handling it would require libc for no benefit.
//!
//! Output is one JSON line per poll — a COMPLETED-WORK record carrying observed values, not a
//! heartbeat. `active (running)` is not evidence of work; a poll with real numbers is.

use std::fs;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Duration;

/// N3 documents a 16 GB available-RAM floor. Note the Python guard also reports
/// `oom_guard.RAM_LOAD_BUFFER_GB = 8.0`, which is a DIFFERENT quantity (headroom to keep free
/// *after* a load completes, vs the floor below which no heavy load may start). This binary alerts
/// on the stricter floor. That discrepancy is filed for reconciliation — do not silently collapse
/// them here.
const FLOOR_GB: f64 = 16.0;
const ROUTER: &str = "127.0.0.1:13305";
const POLL_SECS: u64 = 60;
/// A ctx_size=0 entry can reappear when the router reloads recipe options from download metadata,
/// so a one-shot audit is insufficient — re-check periodically.
const AUDIT_EVERY: u64 = 30;
/// Models at or above this size are the OOM hazard; footprint tracks ctx_size, not parameter count.
const HEAVY_MODELS: &[&str] = &[
    "Gemma-4-26B-A4B-it-GGUF",
    "Gemma-4-31B-it-GGUF",
    "Qwen3.6-35B-A3B-GGUF",
    "Qwen3.6-35B-A3B-MTP-GGUF",
    "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "Nemotron-3-Nano-30B-A3B-GGUF",
    "Bonsai-27B-gguf-Q1_0",
];

/// Available memory in GB from /proc/meminfo. Returns None rather than a guess: UNKNOWN must never
/// be reported as a safe value.
fn available_gb() -> Option<f64> {
    let text = fs::read_to_string("/proc/meminfo").ok()?;
    for line in text.lines() {
        if let Some(rest) = line.strip_prefix("MemAvailable:") {
            let kb: f64 = rest.split_whitespace().next()?.parse().ok()?;
            return Some(kb / 1024.0 / 1024.0);
        }
    }
    None
}

/// Minimal HTTP/1.1 GET over loopback. Hand-rolled to keep the dependency count at zero.
fn http_get(path: &str) -> Option<String> {
    let mut s = TcpStream::connect(ROUTER).ok()?;
    s.set_read_timeout(Some(Duration::from_secs(5))).ok()?;
    s.set_write_timeout(Some(Duration::from_secs(5))).ok()?;
    let req = format!("GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n");
    s.write_all(req.as_bytes()).ok()?;
    let mut buf = String::new();
    s.read_to_string(&mut buf).ok()?;
    Some(buf)
}

/// Pull an integer field out of a JSON body without a JSON parser. Adequate because we need exactly
/// one numeric field; a real parser would be the only dependency in the binary.
fn json_int(body: &str, key: &str) -> Option<i64> {
    let needle = format!("\"{key}\"");
    let start = body.find(&needle)? + needle.len();
    let tail = &body[start..];
    let colon = tail.find(':')? + 1;
    let digits: String = tail[colon..]
        .chars()
        .skip_while(|c| c.is_whitespace())
        .take_while(|c| c.is_ascii_digit() || *c == '-')
        .collect();
    digits.parse().ok()
}

/// Heavy models whose ctx_size is 0 — the live OOM hazard (unbounded KV cache).
fn ctx_hazards() -> Vec<String> {
    let mut out = Vec::new();
    for m in HEAVY_MODELS {
        if let Some(body) = http_get(&format!("/api/v1/models/{m}")) {
            if json_int(&body, "ctx_size") == Some(0) {
                out.push((*m).to_string());
            }
        }
    }
    out
}

fn main() {
    println!(
        "resource-guard(rust) starting: poll={POLL_SECS}s floor={FLOOR_GB}GB audit_every={AUDIT_EVERY}"
    );
    let mut poll: u64 = 0;
    loop {
        match available_gb() {
            None => println!("{{\"poll\":{poll},\"available_gb\":null,\"status\":\"UNKNOWN\"}}"),
            Some(avail) => {
                let below = avail < FLOOR_GB;
                if below {
                    eprintln!(
                        "WARNING RAM BELOW FLOOR: {avail:.1} GB available < {FLOOR_GB} GB floor \
                         — do not load any heavy model"
                    );
                }
                let hazards = if poll % AUDIT_EVERY == 0 { ctx_hazards() } else { Vec::new() };
                for h in &hazards {
                    eprintln!("ERROR OOM HAZARD: {h} has ctx_size=0 — bound it before any load");
                }
                println!(
                    "{{\"poll\":{poll},\"available_gb\":{avail:.2},\"below_floor\":{below},\"hazards\":{}}}",
                    hazards.len()
                );
            }
        }
        // Flush explicitly: journald reads stdout, and a buffered line is an invisible poll.
        let _ = std::io::stdout().flush();
        poll += 1;
        std::thread::sleep(Duration::from_secs(POLL_SECS));
    }
}
