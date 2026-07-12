# Fase 0 — Findings & Veredicto

Fecha: 2026-07-12. RustDesk server OSS dockerizado, verificado en Acer.

## Qué se verificó

| Pregunta | Resultado |
|----------|-----------|
| ¿hbbs OSS persiste estado? | Sí, sqlite `db_v2.sqlite3` (confirmado en logs `DB_URL=`). |
| ¿Registry de devices recuperable? | ✅ Sí — tabla `peer`: `id`, `pk`, `created_at`. |
| ¿Estado **online** recuperable del sqlite? | ❌ **No.** Sin `last_online`. Presencia vive en RAM del hbbs. |
| ¿API HTTP OSS para presencia? | No (es feature de RustDesk Pro). |
| ¿ACL OSS? | Débil, por-password/pubkey. Confirma estrategia wrapper = control de emisión. |

## Veredicto: **GO-PARCIAL**

El enfoque "wrap" **sigue siendo viable**. RustDesk OSS resuelve todo el motor A/V y da
registry vía sqlite. Pero **la presencia (online/offline) NO se puede leer de hbbs OSS** —
hay que resolverla fuera.

## Impacto en el diseño del MVP

El adapter `rustdesk_state` NO puede dar presencia (solo registry, opcional). Se agrega un
componente que el spec original no tenía:

- **Agent heartbeat:** el agente (daemon systemd en la máquina controlada) pinguea al
  control-plane cada N seg. `online = último_ping < umbral`. Presencia 100% propia,
  hexagonal, sin acoplarse a internals RustDesk ni depender de Pro.

Esto suma: 1 endpoint (`POST /agents/{id}/ping`) + timer en el agente + repo de last-seen.
Bajo costo. El resto del MVP (enroll, dashboard, auth, connect) queda igual.

## Próximo paso

Volver a **brainstorming** para actualizar el spec del MVP con el componente agent-heartbeat
y re-aprobar el diseño antes de planificar/implementar. (Decisión del usuario, 2026-07-12.)

## Estado de artefactos

- `infra/docker-compose.yml` — server OSS funcionando, reusable para el MVP.
- Server pubkey (este entorno): `AGp+zEaE0i+imMuyTR+oY4ikXOX2A3DmoZj0h8lvjZQ=` (se regenera si se borra `infra/data/`).
- Tasks 3-4 del plan de spike (domain + adapter sqlite) **no ejecutadas** — el hallazgo del
  schema hizo innecesario el resto del spike.
