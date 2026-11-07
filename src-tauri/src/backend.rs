//! Own the bundled backend and its startup handshake for one desktop session.

use serde::Deserialize;
use std::{
    fs::{self, DirBuilder, OpenOptions},
    io::{self, Read, Write},
    net::{Ipv4Addr, SocketAddrV4, TcpStream},
    path::{Path, PathBuf},
    process::{Child, Command, ExitStatus, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Mutex,
    },
    thread,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

#[cfg(unix)]
use std::os::unix::{fs::DirBuilderExt, process::CommandExt};

const STARTUP_TIMEOUT: Duration = Duration::from_secs(60);
const POLL_INTERVAL: Duration = Duration::from_millis(100);
const HEALTH_TIMEOUT: Duration = Duration::from_millis(300);
const STOP_TIMEOUT: Duration = Duration::from_secs(2);

#[derive(Deserialize)]
struct Readiness {
    port: u16,
    pid: u32,
}

#[derive(Deserialize)]
struct Health {
    status: String,
    service: String,
}

/// Each launch owns a private directory; it cannot consume another launch's port.
struct ReadyDirectory(PathBuf);

impl ReadyDirectory {
    fn create() -> io::Result<Self> {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(io::Error::other)?
            .as_nanos();
        let path =
            std::env::temp_dir().join(format!("speech-guider-{}-{nonce}", std::process::id()));
        let mut builder = DirBuilder::new();
        #[cfg(unix)]
        builder.mode(0o700);
        builder.create(&path)?;
        Ok(Self(path))
    }

    fn file(&self) -> PathBuf {
        self.0.join("ready.json")
    }
}

impl Drop for ReadyDirectory {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

struct Backend {
    child: Child,
    ready: ReadyDirectory,
}

impl Backend {
    fn spawn(
        executable: &Path,
        data_dir: &Path,
        log_path: &Path,
        bundled_assets: &Path,
    ) -> io::Result<Self> {
        fs::create_dir_all(data_dir)?;
        let ready = ReadyDirectory::create()?;
        let log = OpenOptions::new()
            .create(true)
            .append(true)
            .open(log_path)?;
        let mut command = Command::new(executable);
        command
            .arg("--ready-file")
            .arg(ready.file())
            .arg("--parent-pid")
            .arg(std::process::id().to_string())
            .current_dir(data_dir)
            .stdin(Stdio::null())
            .stdout(Stdio::from(log.try_clone()?))
            .stderr(Stdio::from(log));
        if std::env::var_os("SPEECH_GUIDER_PRESETS_FILE").is_none() {
            command.env("SPEECH_GUIDER_PRESETS_FILE", data_dir.join("presets.json"));
        }
        if std::env::var_os("SPEECH_GUIDER_ASSET_DIR").is_none() {
            let assets = if bundled_assets.is_dir() {
                bundled_assets.to_path_buf()
            } else {
                let local = data_dir.join("assets");
                fs::create_dir_all(&local)?;
                local
            };
            command.env("SPEECH_GUIDER_ASSET_DIR", assets);
        }

        // TTS and ffmpeg subprocesses inherit this group so they die with the app.
        #[cfg(unix)]
        command.process_group(0);

        Ok(Self {
            child: command.spawn()?,
            ready,
        })
    }
}

impl Drop for Backend {
    fn drop(&mut self) {
        #[cfg(unix)]
        {
            let group = -(self.child.id() as libc::pid_t);
            // SAFETY: the child was spawned as the leader of its own group.
            let _ = unsafe { libc::kill(group, libc::SIGTERM) };
            let deadline = Instant::now() + STOP_TIMEOUT;
            while Instant::now() < deadline {
                let _ = self.child.try_wait();
                // SAFETY: signal zero only checks whether the group still exists.
                if unsafe { libc::kill(group, 0) } == -1
                    && io::Error::last_os_error().raw_os_error() == Some(libc::ESRCH)
                {
                    break;
                }
                thread::sleep(Duration::from_millis(20));
            }
            // SAFETY: any surviving members still belong to the owned child group.
            let _ = unsafe { libc::kill(group, libc::SIGKILL) };
        }
        #[cfg(not(unix))]
        let _ = self.child.kill();

        let _ = self.child.wait();
    }
}

/// Process ownership stays in native state rather than the background monitor.
#[derive(Default)]
pub struct BackendState {
    active: Mutex<Option<Backend>>,
    stopping: AtomicBool,
}

impl BackendState {
    pub fn spawn(
        &self,
        executable: &Path,
        data_dir: &Path,
        log_path: &Path,
        bundled_assets: &Path,
    ) -> io::Result<()> {
        let mut active = self
            .active
            .lock()
            .map_err(|_| io::Error::other("Backend state lock poisoned"))?;
        if active.is_some() {
            return Err(io::Error::other("The backend is already running."));
        }
        *active = Some(Backend::spawn(
            executable,
            data_dir,
            log_path,
            bundled_assets,
        )?);
        Ok(())
    }

    pub fn wait_for_ready(&self) -> io::Result<Option<u16>> {
        let (path, pid) = {
            let active = self
                .active
                .lock()
                .map_err(|_| io::Error::other("Backend state lock poisoned"))?;
            let Some(backend) = active.as_ref() else {
                return Ok(None);
            };
            (backend.ready.file(), backend.child.id())
        };

        let deadline = Instant::now() + STARTUP_TIMEOUT;
        while Instant::now() < deadline {
            if self.is_stopping() {
                return Ok(None);
            }
            if let Some(status) = self.try_wait()? {
                return Err(io::Error::other(format!(
                    "The backend exited during startup ({status})."
                )));
            }
            match fs::read_to_string(&path) {
                Ok(content) => {
                    let port = parse_ready_port(&content, pid)?;
                    if health_is_ready(port) && self.try_wait()?.is_none() && !self.is_stopping() {
                        return Ok(Some(port));
                    }
                }
                Err(error) if error.kind() == io::ErrorKind::NotFound => {}
                Err(error) => return Err(error),
            }
            thread::sleep(POLL_INTERVAL);
        }
        Err(io::Error::new(
            io::ErrorKind::TimedOut,
            "The backend did not become ready within 60 seconds.",
        ))
    }

    pub fn wait_for_exit(&self) -> io::Result<Option<ExitStatus>> {
        while !self.is_stopping() {
            if let Some(status) = self.try_wait()? {
                return Ok(Some(status));
            }
            thread::sleep(POLL_INTERVAL);
        }
        Ok(None)
    }

    fn try_wait(&self) -> io::Result<Option<ExitStatus>> {
        self.active
            .lock()
            .map_err(|_| io::Error::other("Backend state lock poisoned"))?
            .as_mut()
            .map_or(Ok(None), |backend| backend.child.try_wait())
    }

    pub fn is_stopping(&self) -> bool {
        self.stopping.load(Ordering::Acquire)
    }

    pub fn stop(&self) {
        self.stopping.store(true, Ordering::Release);
        self.terminate();
    }

    pub fn terminate(&self) {
        let child = self
            .active
            .lock()
            .unwrap_or_else(|error| error.into_inner())
            .take();
        drop(child);
    }
}

fn parse_ready_port(content: &str, expected_pid: u32) -> io::Result<u16> {
    let ready: Readiness = serde_json::from_str(content)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    if ready.pid != expected_pid || ready.port == 0 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "The readiness file does not match the running backend.",
        ));
    }
    Ok(ready.port)
}

fn health_is_ready(port: u16) -> bool {
    let address = SocketAddrV4::new(Ipv4Addr::LOCALHOST, port);
    let result = (|| -> io::Result<String> {
        let mut stream = TcpStream::connect_timeout(&address.into(), HEALTH_TIMEOUT)?;
        stream.set_read_timeout(Some(HEALTH_TIMEOUT))?;
        stream.set_write_timeout(Some(HEALTH_TIMEOUT))?;
        write!(
            stream,
            "GET /health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: close\r\n\r\n"
        )?;
        let mut response = String::new();
        stream.take(4096).read_to_string(&mut response)?;
        Ok(response)
    })();
    result.is_ok_and(|response| is_speech_guider_health(&response))
}

fn is_speech_guider_health(response: &str) -> bool {
    let Some((headers, body)) = response.split_once("\r\n\r\n") else {
        return false;
    };
    let status = headers
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1));
    status == Some("200")
        && serde_json::from_str::<Health>(body).is_ok_and(|health| {
            health.status == "ok" && health.service == "pronunciation-evaluator"
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn readiness_must_identify_child_and_nonzero_port() {
        assert_eq!(
            parse_ready_port(r#"{"port":12345,"pid":20}"#, 20).unwrap(),
            12345
        );
        assert!(parse_ready_port(r#"{"port":12345,"pid":21}"#, 20).is_err());
        assert!(parse_ready_port(r#"{"port":0,"pid":20}"#, 20).is_err());
        assert!(parse_ready_port(r#"{"port":65536,"pid":20}"#, 20).is_err());
        assert!(parse_ready_port(r#"{"port":12345}"#, 20).is_err());
    }

    #[test]
    fn health_requires_ok_response_from_speech_guider() {
        let response = |status, service| {
            format!(
                "HTTP/1.1 {status} OK\r\nContent-Type: application/json\r\n\r\n{{\"status\":\"ok\",\"service\":\"{service}\"}}"
            )
        };
        assert!(is_speech_guider_health(&response(
            200,
            "pronunciation-evaluator"
        )));
        assert!(!is_speech_guider_health(&response(
            503,
            "pronunciation-evaluator"
        )));
        assert!(!is_speech_guider_health(&response(200, "other-service")));
    }

    #[test]
    fn readiness_directories_are_separate_and_removed_on_drop() {
        let first = ReadyDirectory::create().unwrap();
        let second = ReadyDirectory::create().unwrap();
        assert_ne!(first.file(), second.file());
        let path = first.0.clone();
        fs::write(first.file(), "{}").unwrap();
        drop(first);
        assert!(!path.exists());
        assert!(second.0.is_dir());
    }

    #[cfg(unix)]
    #[test]
    fn drop_stops_backend_process_group_and_removes_handshake() {
        let ready = ReadyDirectory::create().unwrap();
        let path = ready.file();
        let child = Command::new("/bin/sh")
            .args(["-c", "sleep 60 & echo $! > \"$1\"; wait", "test"])
            .arg(&path)
            .process_group(0)
            .spawn()
            .unwrap();
        let owned = Backend { child, ready };
        let deadline = Instant::now() + Duration::from_secs(2);
        let descendant = loop {
            if let Ok(content) = fs::read_to_string(&path) {
                if let Ok(pid) = content.trim().parse::<libc::pid_t>() {
                    break pid;
                }
            }
            assert!(Instant::now() < deadline, "child never started");
            thread::sleep(Duration::from_millis(10));
        };
        drop(owned);
        assert!(!path.exists());
        let deadline = Instant::now() + Duration::from_secs(2);
        // SAFETY: signal zero checks existence; it does not send a signal.
        while unsafe { libc::kill(descendant, 0) } == 0 {
            assert!(Instant::now() < deadline, "descendant survived cleanup");
            thread::sleep(Duration::from_millis(10));
        }
    }
}
