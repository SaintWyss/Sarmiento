import { invoke } from "@tauri-apps/api/core";
import { getCurrent, onOpenUrl } from "@tauri-apps/plugin-deep-link";
import { disable, enable, isEnabled } from "@tauri-apps/plugin-autostart";
import "./styles.css";
import type {
  Dashboard,
  Device,
  EnrollmentToken,
  MfaEnable,
  MfaSetup,
  WorkstationStatus
} from "./types";
import { button, el, errorMessage, field, formatDate, input, showToast } from "./ui";

const appRoot = document.querySelector<HTMLDivElement>("#app");
if (!appRoot) throw new Error("Application root was not found");
const root: HTMLDivElement = appRoot;

let dashboard: Dashboard | null = null;
let refreshTimer: number | null = null;
const serverKey = "sarmiento.serverUrl";
const usernameKey = "sarmiento.username";

async function call<T>(command: string, args: Record<string, unknown> = {}): Promise<T> {
  return invoke<T>(command, args);
}

async function safe(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    showToast(errorMessage(error), true);
  }
}

function clearRefresh(): void {
  if (refreshTimer !== null) window.clearInterval(refreshTimer);
  refreshTimer = null;
}

function serverUrl(): string {
  return localStorage.getItem(serverKey) || "https://sarmiento.lan";
}

function renderLogin(): void {
  clearRefresh();
  dashboard = null;
  root.replaceChildren();

  const server = input("url", "https://sarmiento.lan");
  server.value = serverUrl();
  server.required = true;
  const username = input("text", "owner");
  username.value = localStorage.getItem(usernameKey) || "owner";
  username.autocomplete = "username";
  const password = input("password", "••••••••••••");
  password.autocomplete = "current-password";
  password.required = true;
  const verification = input("text", "Código MFA o recuperación");
  verification.autocomplete = "one-time-code";

  const submit = button("Ingresar", "primary full", () => undefined);
  submit.type = "submit";
  const error = el("p", { className: "form-error", attrs: { role: "alert" } });
  const form = el(
    "form",
    {
      className: "login-form",
      on: {
        submit: (event) => {
          event.preventDefault();
          submit.disabled = true;
          submit.textContent = "Conectando…";
          error.textContent = "";
          void safe(async () => {
            dashboard = await call<Dashboard>("login", {
              serverUrl: server.value,
              username: username.value,
              password: password.value,
              verificationCode: verification.value || null
            });
            localStorage.setItem(serverKey, server.value.replace(/\/$/, ""));
            localStorage.setItem(usernameKey, username.value);
            password.value = "";
            renderDashboard();
          }).finally(() => {
            submit.disabled = false;
            submit.textContent = "Ingresar";
          });
        }
      }
    },
    field("Servidor Sarmiento", server),
    field("Usuario", username),
    field("Contraseña", password),
    field("MFA (si está activado)", verification),
    submit,
    error
  );

  const brand = el(
    "section",
    { className: "login-brand" },
    el("div", { className: "logo large", text: "S" }),
    el("p", { className: "eyebrow", text: "SARMIENTO DESKTOP" }),
    el("h1", { text: "Todas tus máquinas. Una sola estación." }),
    el("p", {
      className: "muted lead",
      text: "Control nativo y privado para Deskflow y RustDesk, conectado a tu propia infraestructura."
    }),
    el("div", { className: "privacy-chip", text: "● HTTPS · Self-hosted · Sin nube de terceros" })
  );
  const card = el(
    "section",
    { className: "login-card" },
    el("p", { className: "eyebrow", text: "INICIAR SESIÓN" }),
    el("h2", { text: "Conectar al control-plane" }),
    el("p", { className: "muted", text: "La sesión vive únicamente dentro de esta aplicación." }),
    form
  );
  root.append(el("main", { className: "login-layout" }, brand, card));
  password.focus();
}

async function refreshDashboard(silent = false): Promise<void> {
  try {
    dashboard = await call<Dashboard>("dashboard");
    renderDashboard();
    if (!silent) showToast("Equipos actualizados");
  } catch (error) {
    if (!silent) showToast(errorMessage(error), true);
  }
}

function statCard(label: string, value: number, tone = ""): HTMLElement {
  return el(
    "article",
    { className: `stat-card ${tone}` },
    el("span", { text: label }),
    el("strong", { text: String(value) })
  );
}

function modePanel(status: WorkstationStatus | null): HTMLElement {
  const integrated = status?.mode !== "remote";
  return el(
    "section",
    { className: "station-panel" },
    el("div", { className: "station-symbol", text: integrated ? "↔" : "▣" }),
    el(
      "div",
      { className: "station-content" },
      el(
        "div",
        { className: "station-heading" },
        el(
          "div",
          {},
          el("p", { className: "eyebrow", text: "ESTACIÓN DE TRABAJO" }),
          el("h2", { text: integrated ? "Pantallas físicas activas" : "Control remoto activo" })
        ),
        el("span", {
          className: `status-pill ${integrated ? "online" : "remote"}`,
          text: integrated ? "Deskflow activo" : "Deskflow pausado"
        })
      ),
      el("p", {
        className: "muted",
        text: integrated
          ? "Mové el cursor entre la PC y la notebook como un único escritorio."
          : "La notebook está preparada para verse dentro de uno de tus monitores."
      }),
      el(
        "div",
        { className: "inline-actions" },
        button("Usar pantallas físicas", integrated ? "secondary" : "primary", () => {
          void safe(async () => {
            await call("set_integrated_mode");
            showToast("Deskflow activado");
            await refreshDashboard(true);
          });
        }),
        el("span", {
          className: "service-detail",
          text: status ? `${status.deskflow_unit} · RustDesk ${status.rustdesk}` : "Detectando servicios…"
        })
      )
    )
  );
}

function deviceCard(device: Device): HTMLElement {
  const tags = el("div", { className: "tags" });
  for (const value of [device.platform, device.architecture, ...device.tags].filter(Boolean)) {
    tags.append(el("span", { className: "tag", text: value }));
  }
  if (device.credential_rotation_pending) tags.append(el("span", { className: "tag warning", text: "rotación pendiente" }));

  const remote = button("Control remoto", "primary", () => connectDevice(device, false));
  const monitor = button("Abrir en monitor", "light", () => connectDevice(device, true));
  monitor.disabled = !device.online;
  remote.disabled = !device.online;

  return el(
    "article",
    { className: `device-card ${device.online ? "is-online" : ""}` },
    el(
      "div",
      { className: "device-top" },
      el("span", { className: `presence ${device.online ? "online" : ""}`, text: device.online ? "En línea" : "Fuera de línea" }),
      el("time", { text: formatDate(device.last_seen) })
    ),
    el("div", { className: "device-glyph", text: device.platform.toLowerCase().includes("linux") ? "⌘" : "▣" }),
    el("h3", { text: device.alias }),
    el("p", { className: "device-id", text: `RustDesk · ${device.rustdesk_id}` }),
    tags,
    el(
      "div",
      { className: "device-actions" },
      remote,
      monitor,
      button("Administrar", "ghost", () => openDeviceDialog(device))
    )
  );
}

function connectDevice(device: Device, pauseDeskflow: boolean): void {
  void safe(async () => {
    await call("connect_device", { rustdeskId: device.rustdesk_id, pauseDeskflow });
    showToast(pauseDeskflow ? `${device.alias} se abrirá en tu monitor` : `Conectando con ${device.alias}`);
    window.setTimeout(() => { void refreshDashboard(true); }, 800);
  });
}

function auditLabel(action: string): string {
  const labels: Record<string, string> = {
    "auth.login_succeeded": "Inicio de sesión",
    "auth.logout": "Cierre de sesión",
    "auth.password_changed": "Contraseña modificada",
    "auth.mfa_enabled": "MFA activado",
    "device.enrolled": "Equipo enrolado",
    "device.updated": "Equipo actualizado",
    "device.revoked": "Equipo revocado",
    "device.credential_rotation_requested": "Rotación solicitada"
  };
  return labels[action] || action;
}

function renderDashboard(): void {
  if (!dashboard) return renderLogin();
  const data = dashboard;
  root.replaceChildren();

  const header = el(
    "header",
    { className: "app-header" },
    el("div", { className: "brand" }, el("div", { className: "logo", text: "S" }), el("div", {}, el("strong", { text: "Sarmiento" }), el("small", { text: `Desktop 1.0 · Server ${data.config.version}` }))),
    el(
      "nav",
      {},
      button("Añadir equipo", "primary compact", openEnrollmentDialog),
      button("Seguridad", "ghost compact", openSecurityDialog),
      button("Ajustes", "ghost compact", openSettingsDialog)
    )
  );

  const search = input("search", "Buscar equipo, plataforma o etiqueta");
  const devices = el("div", { className: "device-grid" });
  const renderDevices = (): void => {
    const term = search.value.trim().toLowerCase();
    const visible = data.devices.filter((device) =>
      [device.alias, device.hostname, device.platform, device.rustdesk_id, ...device.tags].join(" ").toLowerCase().includes(term)
    );
    devices.replaceChildren(...visible.map(deviceCard));
    if (!visible.length) devices.append(el("div", { className: "empty", text: "No hay equipos que coincidan con la búsqueda." }));
  };
  search.addEventListener("input", renderDevices);
  renderDevices();

  const audit = el("div", { className: "audit-list" });
  for (const event of data.audit.slice(0, 12)) {
    audit.append(
      el(
        "div",
        { className: "audit-row" },
        el("span", { text: auditLabel(event.action) }),
        el("small", { text: event.actor_type }),
        el("time", { text: formatDate(event.created_at) })
      )
    );
  }

  const content = el(
    "main",
    { className: "app-shell" },
    header,
    el(
      "section",
      { className: "hero" },
      el("div", {}, el("p", { className: "eyebrow", text: "CENTRO DE OPERACIONES" }), el("h1", { text: "Tus equipos, bajo control." }), el("p", { className: "muted", text: `RustDesk privado · ${data.config.rustdesk_server}` })),
      button("Actualizar", "secondary", () => { void refreshDashboard(); })
    ),
    el(
      "section",
      { className: "stats-grid" },
      statCard("Equipos", data.stats.total_devices),
      statCard("En línea", data.stats.online_devices, "good"),
      statCard("Fuera de línea", data.stats.offline_devices),
      statCard("Revocados", data.stats.revoked_devices, "danger")
    ),
    el("div", { attrs: { id: "mode-slot" } }, modePanel(null)),
    el("section", { className: "devices-section" }, el("div", { className: "section-head" }, el("h2", { text: "Dispositivos" }), search), devices),
    el("section", { className: "audit-panel" }, el("div", { className: "section-head" }, el("h2", { text: "Actividad reciente" }), el("span", { className: "muted", text: data.owner.username })), audit)
  );
  root.append(content);

  void call<WorkstationStatus>("workstation_status")
    .then((status) => document.querySelector("#mode-slot")?.replaceChildren(modePanel(status)))
    .catch(() => document.querySelector("#mode-slot")?.replaceChildren(modePanel(null)));

  clearRefresh();
  refreshTimer = window.setInterval(() => { void refreshDashboard(true); }, 30_000);
}

function dialog(title: string, subtitle: string, ...content: Node[]): HTMLDialogElement {
  const modal = el(
    "dialog",
    {},
    el(
      "form",
      { className: "dialog-card", attrs: { method: "dialog" } },
      button("×", "dialog-close", () => modal.close()),
      el("p", { className: "eyebrow", text: subtitle }),
      el("h2", { text: title }),
      ...content
    )
  );
  document.body.append(modal);
  modal.addEventListener("close", () => modal.remove(), { once: true });
  modal.showModal();
  return modal;
}

function openDeviceDialog(device: Device): void {
  const alias = input("text");
  alias.value = device.alias;
  const tags = input("text", "casa, notebook, trabajo");
  tags.value = device.tags.join(", ");
  let modal: HTMLDialogElement;
  modal = dialog(
    device.alias,
    "ADMINISTRAR DISPOSITIVO",
    field("Alias", alias),
    field("Etiquetas", tags),
    button("Guardar cambios", "primary full", () => {
      void safe(async () => {
        await call("update_device", {
          deviceId: device.id,
          alias: alias.value,
          tags: tags.value.split(",").map((item) => item.trim()).filter(Boolean)
        });
        modal.close();
        await refreshDashboard(true);
        showToast("Dispositivo actualizado");
      });
    }),
    button("Rotar credencial del agente", "secondary full", () => {
      if (!window.confirm("¿Solicitar una rotación segura en el próximo heartbeat?")) return;
      void safe(async () => {
        await call("rotate_device_token", { deviceId: device.id });
        modal.close();
        await refreshDashboard(true);
      });
    }),
    button("Revocar dispositivo", "danger-button full", () => {
      if (!window.confirm("El agente perderá acceso hasta volver a enrolarlo. ¿Continuar?")) return;
      void safe(async () => {
        await call("revoke_device", { deviceId: device.id });
        modal.close();
        await refreshDashboard(true);
      });
    })
  );
}

function openEnrollmentDialog(): void {
  const label = input("text", "Notebook personal");
  const ttl = input("number");
  ttl.value = "60";
  ttl.min = "15";
  ttl.max = "1440";
  const output = el("div", { className: "token-output hidden" });
  dialog(
    "Añadir equipo",
    "ENROLAMIENTO SEGURO",
    el("p", { className: "muted", text: "Generá un token de un solo uso y ejecutá el instalador en el equipo nuevo." }),
    field("Nombre de referencia", label),
    field("Validez en minutos", ttl),
    button("Crear token", "primary full", () => {
      void safe(async () => {
        const issued = await call<EnrollmentToken>("create_enrollment_token", {
          label: label.value,
          ttlMinutes: Number(ttl.value)
        });
        const command = `curl -fsSL ${serverUrl()}/agent/install-linux.sh | sudo bash -s -- --url ${serverUrl()} --token '${issued.token}'`;
        const pre = el("pre", { text: command });
        output.classList.remove("hidden");
        output.replaceChildren(
          el("p", { className: "warning-text", text: "Se muestra una sola vez. Vence " + formatDate(issued.expires_at) }),
          pre,
          button("Copiar comando", "secondary full", () => {
            void navigator.clipboard.writeText(command).then(() => showToast("Comando copiado"));
          })
        );
      });
    }),
    output
  );
}

function openSecurityDialog(): void {
  if (!dashboard) return;
  const current = input("password", "Contraseña actual");
  const next = input("password", "Nueva contraseña (mínimo 12)");
  const code = input("text", "Código MFA");
  const mfaBox = el("div", { className: "security-box" });
  let modal: HTMLDialogElement;
  const renderMfa = (): void => {
    mfaBox.replaceChildren();
    if (dashboard?.owner.mfa_enabled) {
      mfaBox.append(
        el("strong", { text: "MFA está activado" }),
        el("p", { className: "muted", text: "Para desactivarlo necesitás la contraseña y un código vigente." }),
        field("Contraseña", current),
        field("Código", code),
        button("Desactivar MFA", "danger-button full", () => {
          void safe(async () => {
            await call("disable_mfa", { currentPassword: current.value, code: code.value });
            modal.close();
            renderLogin();
            showToast("MFA desactivado. Iniciá sesión nuevamente.");
          });
        })
      );
    } else {
      mfaBox.append(
        el("strong", { text: "MFA todavía no está activado" }),
        el("p", { className: "muted", text: "Protegé la cuenta con una aplicación TOTP." }),
        button("Configurar MFA", "secondary full", () => {
          void safe(async () => {
            const setup = await call<MfaSetup>("setup_mfa");
            const verify = input("text", "Código de 6 dígitos");
            mfaBox.replaceChildren(
              field("Clave secreta", Object.assign(input("text"), { value: setup.secret, readOnly: true })),
              el("pre", { text: setup.provisioning_uri }),
              field("Código", verify),
              button("Verificar y activar", "primary full", () => {
                void safe(async () => {
                  const enabled = await call<MfaEnable>("enable_mfa", { secret: setup.secret, code: verify.value });
                  mfaBox.replaceChildren(
                    el("p", { className: "warning-text", text: "Guardá estos códigos ahora. No volverán a mostrarse." }),
                    el("pre", { text: enabled.recovery_codes.join("\n") }),
                    button("Copiar códigos", "secondary full", () => {
                      void navigator.clipboard.writeText(enabled.recovery_codes.join("\n"));
                    })
                  );
                });
              })
            );
          });
        })
      );
    }
  };
  renderMfa();
  modal = dialog(
    "Seguridad de la cuenta",
    "PROPIETARIO",
    mfaBox,
    el("hr"),
    el("h3", { text: "Cambiar contraseña" }),
    field("Contraseña actual", current),
    field("Nueva contraseña", next),
    button("Cambiar contraseña", "primary full", () => {
      void safe(async () => {
        await call("change_password", { currentPassword: current.value, newPassword: next.value });
        modal.close();
        renderLogin();
        showToast("Contraseña cambiada. Iniciá sesión nuevamente.");
      });
    })
  );
}

function openSettingsDialog(): void {
  const server = input("url");
  server.value = serverUrl();
  const auto = el("input", { attrs: { type: "checkbox" } });
  const autoRow = el("label", { className: "toggle-row" }, auto, el("span", { text: "Iniciar Sarmiento con KDE" }));
  void isEnabled().then((value) => { auto.checked = value; });
  auto.addEventListener("change", () => {
    void safe(async () => {
      if (auto.checked) await enable();
      else await disable();
      showToast(auto.checked ? "Inicio automático activado" : "Inicio automático desactivado");
    });
  });
  let modal: HTMLDialogElement;
  modal = dialog(
    "Ajustes",
    "SARMIENTO DESKTOP",
    field("Servidor", server),
    autoRow,
    button("Guardar servidor", "primary full", () => {
      localStorage.setItem(serverKey, server.value.replace(/\/$/, ""));
      modal.close();
      showToast("Servidor guardado. Iniciá sesión nuevamente.");
      void call("logout").catch(() => undefined).finally(renderLogin);
    }),
    button("Cerrar sesión", "secondary full", () => {
      void call("logout").catch(() => undefined).finally(() => {
        modal.close();
        renderLogin();
      });
    })
  );
}

async function handleDeepLink(value: string): Promise<void> {
  try {
    const url = new URL(value);
    if (url.protocol !== "sarmiento:") return;
    if (url.hostname === "connect") {
      const id = url.pathname.replace(/^\//, "");
      await call("connect_device", { rustdeskId: id, pauseDeskflow: false });
    } else if (url.hostname === "workstation" && url.pathname === "/normal") {
      await call("set_integrated_mode");
    } else if (url.hostname === "workstation" && url.pathname.startsWith("/notebook/")) {
      await call("connect_device", { rustdeskId: url.pathname.split("/").at(-1), pauseDeskflow: true });
    }
  } catch (error) {
    showToast(errorMessage(error), true);
  }
}

async function initializeDeepLinks(): Promise<void> {
  const current = await getCurrent();
  for (const value of current ?? []) await handleDeepLink(value);
  await onOpenUrl((urls) => {
    for (const value of urls) void handleDeepLink(value);
  });
}

renderLogin();
void initializeDeepLinks();
