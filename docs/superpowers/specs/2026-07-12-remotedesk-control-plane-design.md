# RemoteDesk — Control-Plane hexagonal sobre RustDesk

> Diseño validado. Fecha: 2026-07-12. Estado: aprobado, pendiente de plan de implementación.
> Nombre del proyecto: **pendiente** (placeholder `remotedesk`).

## Objetivo

Herramienta tipo AnyDesk para manejar los PCs propios (y cualquier máquina futura
que se arme). Control remoto completo: **pantalla + control mouse/teclado**.

Decisión clave: **no reinventar** el motor A/V. Se usa **RustDesk OSS** (Rust,
AGPL, self-hosteable) como caja negra que resuelve captura, encode, NAT traversal
y crypto E2E. Se construye una **capa de control hexagonal propia** (Python/FastAPI)
que aporta el cerebro: inventario de máquinas, enrolamiento, estado online, auth y
dashboard.

## No-objetivos (v1)

- No se toca el código de RustDesk (se corre vía Docker, sin fork).
- No se reimplementa protocolo de video/input.
- Diferido: ACL multiusuario/teams, grabación de sesión, agente Windows, viewer móvil.

## Arquitectura

Tres piezas independientes:

### 1. RustDesk OSS (motor A/V — NO se modifica)

Self-hosteado vía Docker:
- `hbbs` — rendezvous/signal server (UDP 21116)
- `hbbr` — relay server, fallback cuando P2P/NAT falla (TCP 21117)

Provee: captura de pantalla (pipewire portal en Wayland / XSHM en X11), encode de
video, NAT traversal (P2P directo con fallback a relay), crypto E2E. Los clientes
(agente y viewer) apuntan a **este** server y usan **esta** key.

### 2. Agente Linux (máquina controlada)

Cliente RustDesk corriendo como daemon systemd. Su config apunta al server
self-hosteado + key pública propia. Se instala vía el flujo de enrolamiento del
control-plane.

Captura Wayland = punto duro (portal/pipewire, requiere permisos). X11 más simple.
RustDesk ya soporta ambos.

### 3. Control-plane (lo que se construye — Python/FastAPI, hexagonal)

El molde hexagonal replica el estándar de `sme-cyber`: `domain` / `application` /
`adapters`, con gate de tests obligatorio en repo + CI.

```
control-plane/
  domain/       Device, Session, AccessGrant, Enrollment  (entidades + reglas puras)
  application/  enroll_device, list_devices, grant_access, revoke_access, session_log
                (use-cases, dependen solo de ports/protocols)
  adapters/     rustdesk_state   — lee estado de peers desde hbbs
                postgres_repo    — persistencia de devices/grants/sessions
                web_api          — FastAPI (endpoints REST)
                auth             — pairing token estilo wyss (TOFU)
  front/        dashboard web    — lista máquinas, online/offline, botón "conectar"
```

**Regla hexagonal:** `domain` y `application` no importan nada de infra. Los adapters
implementan ports (Protocols). RustDesk se toca **solo** desde `adapters/rustdesk_state`.

### Elección de stack: Python/FastAPI (no Rust)

Razón: el control-plane le habla a RustDesk **por red/estado**, no comparte código con
él. Compartir lenguaje con el motor no ahorra nada real. Python/FastAPI reutiliza el
molde hexagonal ya battle-tested de sme-cyber + skills (`fastapi-templates`,
`python-testing-patterns`). Rust solo convendría si se tocara el motor A/V — y no se hace.

## Fase 0 — Spike make-or-break (ANTES de codear)

Todo el valor del wrapper depende de **cuánto expone el `hbbs` OSS**. Su capa rica
(inventario/permisos/console) es lo que RustDesk vende en **Pro** (de pago). El spike
debe verificar, con RustDesk OSS dockerizado:

1. **Estado de peers online:** ¿se puede leer? Hipótesis: sqlite `db_v2.sqlite3` de hbbs.
2. **Provisioning:** generar config por-device (server addr + key público + password fijo)
   e instalarla en un agente de prueba, que registre y aparezca.
3. **ACL:** confirmar que en OSS el control de acceso es débil (password por device).
   El wrapper reimplementa ACL fino controlando **emisión/rotación de passwords**.

**Criterio de salida:** si no se puede leer estado online ni provisionar sin la capa Pro,
se replantea el enfoque (posible: base sobre RustDesk Pro, o Fork parcial). No se avanza
a implementación hasta cerrar el spike.

## MVP v1 (alcance de corte)

1. Self-host RustDesk server (Docker compose).
2. **Enroll:** endpoint FastAPI que emite config de device + unit systemd que la instala.
3. **Registry + estado online:** adapter que lee estado de hbbs.
4. **Dashboard:** lista de devices, online/offline, botón conectar 1-click (lanza viewer
   con device-ID + password).
5. **Auth** del dashboard: token pairing estilo wyss (TOFU).

## Flujos

- **Enroll:** dashboard → use-case `enroll_device` → emite config → agente la instala →
  registra en hbbs → aparece online en el dashboard.
- **Connect:** dashboard "conectar" → lanza viewer (cliente RustDesk) con device-ID +
  password → RustDesk hace P2P/relay A/V → se controla la máquina.

## Testing (mismo gate que sme-cyber)

- `domain/` + `application/`: unit puro, sin RustDesk ni infra.
- `adapters/`: integración contra `hbbs` dockerizado.
- Tests EN repo + gate obligatorio + CI (política vigente sme, post PR#18).

## Licencia

RustDesk es AGPL. Se corre sin modificar y sin distribuir → sin obligaciones extra para
uso propio. Si en el futuro se distribuye un fork modificado, aplican obligaciones AGPL
(publicar cambios).

## Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| hbbs OSS no expone estado online | Alto (mata el dashboard) | Fase 0 spike antes de codear |
| Captura Wayland requiere permisos/portal | Medio | RustDesk ya lo soporta; fallback X11 |
| ACL fino no viable sin Pro | Medio | Reimplementar vía rotación de passwords |

## Decisiones abiertas

- **Nombre del proyecto:** pendiente (renombrar dir `remotedesk`).
