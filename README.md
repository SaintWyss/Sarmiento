# Sarmiento

AnyDesk propio para manejar los PCs propios y cualquier máquina futura. Control remoto
**pantalla + mouse/teclado**.

**Enfoque:** no se reinventa el motor A/V. **RustDesk OSS** (self-host, Docker) hace
captura/encode/NAT/crypto. Encima se construye un **control-plane hexagonal (Python/FastAPI)**
que aporta el cerebro: enrolamiento, presencia por heartbeat, inventario, auth, dashboard y
conexión 1-click. El control-plane **nunca** toca el código ni el sqlite de RustDesk.

## Estado

📋 **Planificación cerrada — construcción pendiente (la hacés vos).**

| Artefacto | Ruta |
|-----------|------|
| Diseño (spec v2, aprobado) | `docs/superpowers/specs/2026-07-12-remotedesk-control-plane-design.md` |
| Hallazgos Fase 0 (GO-PARCIAL) | `docs/superpowers/specs/FASE0-FINDINGS.md` |
| Bitácora inspección hbbs | `spikes/inspect_hbbs.md` |
| Plan spike Fase 0 (cerrado) | `docs/superpowers/plans/2026-07-12-fase0-spike.md` |
| **Plan de construcción MVP v1** | `docs/superpowers/plans/2026-07-12-mvp-v1.md` |
| Infra RustDesk server (listo) | `infra/docker-compose.yml` |

## Hallazgo clave (Fase 0)

El hbbs OSS **no persiste el estado online** de los peers (vive en RAM; solo RustDesk Pro
lo expone). Por eso la presencia se resuelve con un **agent-heartbeat** propio, y el agente
se auto-registra en el control-plane → una sola fuente de verdad, 100% desacoplado.

## Cómo construir

Seguí el plan MVP tarea por tarea (TDD, commits atómicos):
`docs/superpowers/plans/2026-07-12-mvp-v1.md`. Cada tarea trae el test primero, el código y
el commit. Arranca por la Task 1 (scaffold + domain).

Estructura objetivo:

```
control-plane/   FastAPI hexagonal (domain / application / adapters) — a construir
agent/           installer + heartbeat systemd — a construir
front/           dashboard estático — a construir
infra/           RustDesk server (hbbs+hbbr) [+ postgres en Task 11] — docker compose
docs/ spikes/    diseño, planes, findings
```

## Quickstart (cuando esté construido)

1. `cd infra && docker compose up -d` — server RustDesk (+ Postgres).
2. Levantar el control-plane (`uvicorn src.adapters.web_api:app --port 8000`).
3. Crear un `enroll-token` desde el dashboard.
4. En la máquina a controlar: `CP_URL=... API_TOKEN=... ENROLL_TOKEN=... RD_SERVER=... RD_KEY=... agent/install.sh`.
5. Abrir el dashboard, ver la máquina online, **Conectar**.

## Licencia

RustDesk es AGPL; se corre sin modificar. El control-plane es código propio.
