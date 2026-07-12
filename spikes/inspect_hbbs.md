# Inspección hbbs OSS — bitácora spike Fase 0

Fecha: 2026-07-12. RustDesk server `rustdesk/rustdesk-server:latest` dockerizado (Acer).

## Archivos que genera hbbs (volumen `/root`)

- `db_v2.sqlite3` (+ `-wal`, `-shm`) — DB del rendezvous. Confirmado en logs: `DB_URL=./db_v2.sqlite3`.
- `id_ed25519` / `id_ed25519.pub` — keypair del server (clave pública para configurar clientes).
- `.config/`

Clave pública generada (este server): `AGp+zEaE0i+imMuyTR+oY4ikXOX2A3DmoZj0h8lvjZQ=`

## Schema tabla `peer`

```sql
CREATE TABLE peer (
    guid blob primary key not null,
    id varchar(100) not null,      -- device-ID
    uuid blob not null,
    pk blob not null,              -- clave pública del peer
    created_at datetime not null default(current_timestamp),
    user blob,
    status tinyint,                -- enabled/disabled, NO online/offline
    note varchar(300),
    info text not null
) without rowid;
CREATE UNIQUE INDEX index_peer_id on peer (id);
```

## Hallazgo crítico

- ✅ **Registry recuperable:** `id`, `pk`, `created_at` → listar máquinas conocidas.
- ❌ **Estado online NO está en sqlite.** No hay `last_online` ni timestamp de última
  conexión. `status` tinyint = enabled/disabled, no presencia.
- **Causa:** hbbs mantiene la presencia (peers online) **en memoria RAM**, no la persiste.
  El OSS no expone API HTTP para presencia — es feature de RustDesk Pro.

## Conclusión

La hipótesis "leer online del sqlite de hbbs" **falla**. Presencia hay que resolverla
fuera de hbbs. Ver `docs/superpowers/specs/FASE0-FINDINGS.md`.

(Nota: no se registró un agente real — el schema y la ubicación del estado ya fueron
decisivos para el veredicto, sin necesidad del paso manual.)
