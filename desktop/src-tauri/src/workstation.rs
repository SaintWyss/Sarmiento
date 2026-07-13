use serde::Serialize;
use std::process::{Command, Stdio};

const DESKFLOW_UNITS: [&str; 2] = ["deskflow-server.service", "deskflow-client.service"];

#[derive(Serialize)]
pub struct WorkstationStatus {
    mode: &'static str,
    deskflow_unit: String,
    deskflow: String,
    rustdesk: String,
}

fn valid_rustdesk_id(value: &str) -> bool {
    let length = value.len();
    (3..=64).contains(&length)
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-'))
}

fn systemctl_user(arguments: &[&str]) -> Result<bool, String> {
    let status = Command::new("systemctl")
        .arg("--user")
        .args(arguments)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map_err(|error| format!("No se pudo ejecutar systemctl --user: {error}"))?;
    Ok(status.success())
}

fn unit_exists(unit: &str) -> bool {
    systemctl_user(&["cat", unit]).unwrap_or(false)
}

fn deskflow_unit() -> Result<&'static str, String> {
    DESKFLOW_UNITS
        .into_iter()
        .find(|unit| unit_exists(unit))
        .ok_or_else(|| "No se encontró un servicio Deskflow de usuario".to_string())
}

fn command_available(command: &str) -> bool {
    Command::new(command)
        .arg("--version")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok()
}

#[tauri::command]
pub fn workstation_status() -> Result<WorkstationStatus, String> {
    let unit = deskflow_unit()?;
    let active = systemctl_user(&["is-active", "--quiet", unit])?;
    Ok(WorkstationStatus {
        mode: if active { "integrated" } else { "remote" },
        deskflow_unit: unit.to_string(),
        deskflow: if active { "active" } else { "inactive" }.to_string(),
        rustdesk: if command_available("rustdesk") {
            "disponible"
        } else {
            "no encontrado"
        }
        .to_string(),
    })
}

#[tauri::command]
pub fn set_integrated_mode() -> Result<WorkstationStatus, String> {
    let unit = deskflow_unit()?;
    if !systemctl_user(&["start", unit])? {
        return Err(format!("No se pudo iniciar {unit}"));
    }
    workstation_status()
}

#[tauri::command]
pub fn connect_device(rustdesk_id: String, pause_deskflow: bool) -> Result<(), String> {
    if !valid_rustdesk_id(&rustdesk_id) {
        return Err("El ID de RustDesk contiene caracteres no permitidos".into());
    }
    if pause_deskflow {
        let unit = deskflow_unit()?;
        if !systemctl_user(&["stop", unit])? {
            return Err(format!("No se pudo pausar {unit}"));
        }
    }
    Command::new("rustdesk")
        .arg("--connect")
        .arg(rustdesk_id)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| format!("No se pudo abrir RustDesk: {error}"))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::valid_rustdesk_id;

    #[test]
    fn validates_rustdesk_ids_without_shell_metacharacters() {
        assert!(valid_rustdesk_id("1788088614"));
        assert!(valid_rustdesk_id("desk_01-test"));
        assert!(!valid_rustdesk_id("12"));
        assert!(!valid_rustdesk_id("123; shutdown"));
        assert!(!valid_rustdesk_id("123/../../bin"));
    }
}

