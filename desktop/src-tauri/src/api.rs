use reqwest::{
    cookie::{CookieStore, Jar},
    Client, Method, Url,
};
use serde::Serialize;
use serde_json::{json, Value};
use std::{sync::Arc, time::Duration};
use tokio::sync::Mutex;

const USER_AGENT: &str = concat!("Sarmiento-Desktop/", env!("CARGO_PKG_VERSION"));

#[derive(Clone)]
struct Session {
    base: Url,
    client: Client,
    cookies: Arc<Jar>,
}

#[derive(Default)]
pub struct ApiState {
    session: Mutex<Option<Session>>,
}

#[derive(Serialize)]
pub struct Dashboard {
    owner: Value,
    config: Value,
    devices: Value,
    stats: Value,
    audit: Value,
}

fn normalize_server_url(value: &str) -> Result<Url, String> {
    let trimmed = value.trim().trim_end_matches('/');
    let url = Url::parse(trimmed).map_err(|_| "La URL del servidor no es válida".to_string())?;
    let local_http = url.scheme() == "http"
        && matches!(url.host_str(), Some("localhost" | "127.0.0.1" | "[::1]" | "::1"));
    if url.scheme() != "https" && !local_http {
        return Err("El servidor debe usar HTTPS (HTTP solo se admite en localhost)".into());
    }
    if !url.username().is_empty()
        || url.password().is_some()
        || url.query().is_some()
        || url.fragment().is_some()
        || url.path() != "/"
    {
        return Err("Usá solamente el origen del servidor, por ejemplo https://sarmiento.lan".into());
    }
    Ok(url)
}

fn endpoint(base: &Url, path: &str) -> Result<Url, String> {
    base.join(&format!("api/v1/{}", path.trim_start_matches('/')))
        .map_err(|_| "No se pudo construir la URL del servidor".into())
}

async fn response_json(response: reqwest::Response) -> Result<Value, String> {
    let status = response.status();
    let bytes = response
        .bytes()
        .await
        .map_err(|_| format!("No se pudo leer la respuesta del servidor ({status})"))?;
    if status.is_success() && bytes.is_empty() {
        return Ok(Value::Null);
    }
    let body = serde_json::from_slice::<Value>(&bytes)
        .map_err(|_| format!("El servidor devolvió una respuesta inválida ({status})"))?;
    if status.is_success() {
        return Ok(body);
    }
    let detail = body
        .get("detail")
        .and_then(Value::as_str)
        .unwrap_or("La operación fue rechazada por el servidor");
    Err(detail.to_string())
}

fn csrf_token(session: &Session) -> Result<String, String> {
    let header = session
        .cookies
        .cookies(&session.base)
        .ok_or_else(|| "La sesión no contiene un token CSRF".to_string())?;
    let cookies = header
        .to_str()
        .map_err(|_| "El token CSRF de la sesión no es válido".to_string())?;
    cookies
        .split(';')
        .filter_map(|part| part.trim().split_once('='))
        .find_map(|(name, value)| {
            (matches!(name, "__Host-sarmiento_csrf" | "sarmiento_csrf")
                || name.ends_with("_csrf"))
                .then(|| value.to_string())
        })
        .ok_or_else(|| "La sesión no contiene un token CSRF".to_string())
}

async fn request(
    session: &Session,
    method: Method,
    path: &str,
    payload: Option<Value>,
) -> Result<Value, String> {
    let mut builder = session.client.request(method.clone(), endpoint(&session.base, path)?);
    if method != Method::GET && method != Method::HEAD {
        builder = builder.header("X-Sarmiento-CSRF", csrf_token(session)?);
    }
    if let Some(body) = payload {
        builder = builder.json(&body);
    }
    let response = builder
        .send()
        .await
        .map_err(|error| format!("No se pudo conectar al servidor: {error}"))?;
    response_json(response).await
}

async fn active_session(state: &ApiState) -> Result<Session, String> {
    state
        .session
        .lock()
        .await
        .clone()
        .ok_or_else(|| "La sesión expiró. Iniciá sesión nuevamente.".to_string())
}

async fn load_dashboard(session: &Session) -> Result<Dashboard, String> {
    let (owner, config, devices, stats, audit) = tokio::join!(
        request(session, Method::GET, "auth/me", None),
        request(session, Method::GET, "config/public", None),
        request(session, Method::GET, "devices", None),
        request(session, Method::GET, "stats", None),
        request(session, Method::GET, "audit?limit=30", None),
    );
    Ok(Dashboard {
        owner: owner?,
        config: config?,
        devices: devices?,
        stats: stats?,
        audit: audit?,
    })
}

#[tauri::command]
pub async fn login(
    state: tauri::State<'_, ApiState>,
    server_url: String,
    username: String,
    password: String,
    verification_code: Option<String>,
) -> Result<Dashboard, String> {
    let base = normalize_server_url(&server_url)?;
    let cookies = Arc::new(Jar::default());
    let client = Client::builder()
        .cookie_provider(cookies.clone())
        .connect_timeout(Duration::from_secs(8))
        .timeout(Duration::from_secs(20))
        .user_agent(USER_AGENT)
        .build()
        .map_err(|error| format!("No se pudo iniciar el cliente HTTPS: {error}"))?;
    let session = Session {
        base,
        client,
        cookies,
    };
    let response = session
        .client
        .post(endpoint(&session.base, "auth/login")?)
        .json(&json!({
            "username": username,
            "password": password,
            "verification_code": verification_code.filter(|value| !value.trim().is_empty())
        }))
        .send()
        .await
        .map_err(|error| format!("No se pudo conectar al servidor: {error}"))?;
    response_json(response).await?;
    let dashboard = load_dashboard(&session).await?;
    *state.session.lock().await = Some(session);
    Ok(dashboard)
}

#[tauri::command]
pub async fn dashboard(state: tauri::State<'_, ApiState>) -> Result<Dashboard, String> {
    load_dashboard(&active_session(&state).await?).await
}

#[tauri::command]
pub async fn logout(state: tauri::State<'_, ApiState>) -> Result<(), String> {
    let session = active_session(&state).await?;
    let result = request(&session, Method::POST, "auth/logout", Some(json!({}))).await;
    *state.session.lock().await = None;
    result.map(|_| ())
}

#[tauri::command]
pub async fn update_device(
    state: tauri::State<'_, ApiState>,
    device_id: String,
    alias: String,
    tags: Vec<String>,
) -> Result<Value, String> {
    let session = active_session(&state).await?;
    request(
        &session,
        Method::PATCH,
        &format!("devices/{device_id}"),
        Some(json!({ "alias": alias, "tags": tags })),
    )
    .await
}

#[tauri::command]
pub async fn rotate_device_token(
    state: tauri::State<'_, ApiState>,
    device_id: String,
) -> Result<Value, String> {
    let session = active_session(&state).await?;
    request(
        &session,
        Method::POST,
        &format!("devices/{device_id}/rotate-token"),
        Some(json!({})),
    )
    .await
}

#[tauri::command]
pub async fn revoke_device(
    state: tauri::State<'_, ApiState>,
    device_id: String,
) -> Result<Value, String> {
    let session = active_session(&state).await?;
    request(
        &session,
        Method::POST,
        &format!("devices/{device_id}/revoke"),
        Some(json!({})),
    )
    .await
}

#[tauri::command]
pub async fn create_enrollment_token(
    state: tauri::State<'_, ApiState>,
    label: String,
    ttl_minutes: u32,
) -> Result<Value, String> {
    if !(15..=1440).contains(&ttl_minutes) {
        return Err("La validez debe estar entre 15 y 1440 minutos".into());
    }
    let session = active_session(&state).await?;
    request(
        &session,
        Method::POST,
        "enrollment-tokens",
        Some(json!({ "label": label, "ttl_minutes": ttl_minutes })),
    )
    .await
}

#[tauri::command]
pub async fn change_password(
    state: tauri::State<'_, ApiState>,
    current_password: String,
    new_password: String,
) -> Result<Value, String> {
    let session = active_session(&state).await?;
    let result = request(
        &session,
        Method::POST,
        "auth/change-password",
        Some(json!({ "current_password": current_password, "new_password": new_password })),
    )
    .await;
    if result.is_ok() {
        *state.session.lock().await = None;
    }
    result
}

#[tauri::command]
pub async fn setup_mfa(state: tauri::State<'_, ApiState>) -> Result<Value, String> {
    let session = active_session(&state).await?;
    request(&session, Method::POST, "auth/mfa/setup", Some(json!({}))).await
}

#[tauri::command]
pub async fn enable_mfa(
    state: tauri::State<'_, ApiState>,
    secret: String,
    code: String,
) -> Result<Value, String> {
    let session = active_session(&state).await?;
    let result = request(
        &session,
        Method::POST,
        "auth/mfa/enable",
        Some(json!({ "secret": secret, "code": code })),
    )
    .await;
    if result.is_ok() {
        *state.session.lock().await = None;
    }
    result
}

#[tauri::command]
pub async fn disable_mfa(
    state: tauri::State<'_, ApiState>,
    current_password: String,
    code: String,
) -> Result<Value, String> {
    let session = active_session(&state).await?;
    let result = request(
        &session,
        Method::POST,
        "auth/mfa/disable",
        Some(json!({ "current_password": current_password, "code": code })),
    )
    .await;
    if result.is_ok() {
        *state.session.lock().await = None;
    }
    result
}

#[cfg(test)]
mod tests {
    use super::normalize_server_url;

    #[test]
    fn accepts_https_origin_and_local_development() {
        assert!(normalize_server_url("https://sarmiento.lan/").is_ok());
        assert!(normalize_server_url("http://localhost:8000").is_ok());
    }

    #[test]
    fn rejects_insecure_or_ambiguous_server_urls() {
        assert!(normalize_server_url("http://192.168.1.2").is_err());
        assert!(normalize_server_url("https://user@example.test").is_err());
        assert!(normalize_server_url("https://example.test/panel").is_err());
    }
}
