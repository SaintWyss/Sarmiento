# RemoteDesk — Control-Plane hexagonal sobre RustDesk (v2)

> Diseño validado. Fecha: 2026-07-12. Estado: aprobado. v2 incorpora hallazgo Fase 0.
> Nombre del proyecto: **pendiente** (placeholder `remotedesk`).

## Objetivo

Herramienta tipo AnyDesk para manejar los PCs propios (y cualquier máquina futura
que se arme). Control remoto completo: **pantalla + control mouse/teclado**.

Decisión clave: **no reinventar** el motor A/V. Se usa **RustDesk OSS** (Rust,
AGPL, self-hosteable) como motor que resuelve captura, encode, NAT traversal y
crypto E2E. Se construye una **capa de control hexagonal propia** (Python/FastAPI)
que aporta el cerebro: inventario de máquinas, enrolamiento, presencia, auth y dashboard.

## Hallazgo Fase 0 (cierra el spike) — GO-PARCIAL

Spike ejecutado 2026-07-12 (`docs/superpowers/specs/FASE0-FINDINGS.md`):
- ✅ RustDesk server OSS dockerizado funciona (`infra/docker-compose.yml`).
- ✅ Registry recuperable del sqlite hbbs (`peer.id`, `peer.pk`).
- ❌ **Estado online NO está en el sqlite** — la presencia vive en RAM del hbbs; el OSS
  no la expone (feature Pro). Tabla `peer` no tiene `last_online`.

**Consecuencia:** la presencia se resuelve **fuera de RustDesk**, con un **agent-heartbeat**
al control-plane. Y como el agente ya habla con el control-plane, **se auto-registra** ahí
mismo → el control-plane nunca lee el sqlite de hbbs. Una sola fuente de verdad, 100%
desacoplado de RustDesk.

## No-objetivos (v1)

- No se toca ni forkea el código de RustDesk (se corre vía Docker).
- No se reimplementa protocolo de video/input.
- El control-plane NO lee el sqlite de hbbs (registry propio vía auto-registro del agente).
- Diferido: ACL multiusuario/teams, grabación de sesión, agente Windows, viewer móvil.

## Arquitectura

### 1. RustDesk OSS (motor A/V — NO se modifica, NO se consulta)

Self-hosteado vía Docker (`infra/docker-compose.yml`, ya funcionando del spike):
- `hbbs` — rendezvous/signal (UDP 21116) + `hbbr` — relay (TCP 21117).
- Rol: captura (pipewire/Wayland o XSHM/X11), encode, NAT traversal P2P+relay, crypto E2E.
- Los clientes (agente y viewer) apuntan a este server + su key pública.

### 2. Agente Linux (máquina controlada — daemon systemd)

Tres responsabilidades:
1. **Cliente RustDesk** corriendo, config apuntando al server self-hosteado + key propia.
2. **Enroll (una vez):** `POST /agents {id, pubkey, alias, enroll_token}` — reporta su
   RustDesk-ID y pubkey al control-plane, que lo registra.
3. **Heartbeat (cada 30s):** `POST /agents/{id}/ping` — señal de presencia.

Captura Wayland = punto duro (portal/pipewire, permisos); X11 más simple. RustDesk ya
soporta ambos.

### 3. Control-plane (lo que se construye — Python/FastAPI, hexagonal)

Molde hexagonal estándar sme-cyber: `domain` / `application` / `adapters`, gate de tests.

```
control-plane/
  domain/       Device(id, alias, pubkey, last_seen)  — online = now-last_seen<umbral
                AccessGrant, Session, Enrollment        (entidades + reglas puras)
  application/  enroll_device, heartbeat, list_devices, grant_access, revoke_access
                (use-cases; dependen solo de ports/Protocols)
  adapters/     web_api        — FastAPI (endpoints REST)
                postgres_repo  — persistencia (ÚNICA fuente de verdad)
                auth           — enroll_token (uso único) + pairing token dashboard (TOFU wyss)
  front/        dashboard web  — lista máquinas, online/offline, botón "conectar" 1-click
```

**Regla hexagonal:** `domain` y `application` no importan infra. Ports = Protocols; adapters
los implementan. **No hay adapter que toque RustDesk** (desacople total).

Port principal: `DeviceRepository` — `save(Device)`, `get(id) -> Device | None`,
`list() -> list[Device]`.

### Elección de stack: Python/FastAPI (no Rust)

El control-plane le habla a los agentes por HTTP, no comparte código con RustDesk.
Reutiliza el molde hexagonal battle-tested de sme-cyber + skills (`fastapi-templates`,
`python-testing-patterns`). Rust solo convendría si se tocara el motor A/V — y no se hace.

## MVP v1 (alcance de corte)

1. RustDesk server self-host (Docker compose — **ya hecho** en `infra/`).
2. **Enroll:** endpoint `POST /agents` + `enroll_token` de uso único; script/unit systemd
   del agente que se auto-registra.
3. **Heartbeat + presencia:** endpoint `POST /agents/{id}/ping`; `Device.online` derivado.
4. **Registry + dashboard:** `GET /agents` + front que lista máquinas, online/offline,
   botón conectar 1-click (lanza viewer con device-ID + password).
5. **Auth** del dashboard: pairing token estilo wyss (TOFU).

## Flujos

- **Enroll:** dashboard emite `enroll_token` → se corre el instalador en la máquina →
  agente `POST /agents {id, pubkey, alias, enroll_token}` → queda registrado.
- **Presencia:** agente `POST /agents/{id}/ping` cada 30s → `last_seen` actualizado →
  dashboard muestra online si `now - last_seen < umbral`.
- **Connect:** dashboard "conectar" → lanza viewer (cliente RustDesk) con device-ID +
  password → RustDesk hace P2P/relay A/V → se controla la máquina.

## Testing (mismo gate que sme-cyber)

- `domain/` + `application/`: unit puro, sin infra (fakes de `DeviceRepository`).
- `adapters/`: integración (web_api con TestClient FastAPI; postgres_repo contra DB real/docker).
- Tests EN repo + gate obligatorio + CI (política vigente sme, post PR#18).

## Seguridad

- `enroll_token`: uso único, TTL corto, emitido por el dashboard autenticado.
- Heartbeat/enroll de agentes: autenticados (token por-agente tras enroll).
- Dashboard: pairing token TOFU estilo wyss.
- RustDesk: key pública propia fija en todos los clientes; passwords de device gestionados
  por el control-plane (emisión/rotación = ACL fino que el OSS no da).

## Licencia

RustDesk AGPL: se corre sin modificar ni distribuir → sin obligaciones extra para uso propio.

## Riesgos

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| ~~hbbs OSS no expone online~~ | — | **Resuelto Fase 0:** agent-heartbeat propio |
| Captura Wayland requiere portal/permisos | Medio | RustDesk ya lo soporta; fallback X11 |
| ACL fino no viable sin Pro | Medio | Control-plane gestiona emisión/rotación de passwords |
| Agente offline no reporta pero está prendido | Bajo | umbral de presencia configurable; heartbeat corto |

## Decisiones abiertas

- **Nombre del proyecto:** pendiente (renombrar dir `remotedesk`).
