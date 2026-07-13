# Operaciones

## Estado y logs

```bash
make ps
make logs
curl -fsS https://control.example.com/healthz
curl -fsS https://control.example.com/readyz
```

## Backup

```bash
make backup
```

El backup incluye:

- dump PostgreSQL;
- identidad y datos persistentes de RustDesk;
- copia de `infra/.env`;
- checksums SHA-256.

El directorio contiene secretos. Debe cifrarse antes de copiarlo fuera del servidor.

## Restore

```bash
./ops/restore.sh backups/<timestamp>
make up
make smoke URL=https://control.example.com
```

Después del restore, validar que la clave pública RustDesk coincide con la configurada en clientes existentes.

## Alertas manuales mínimas

- Contenedor reiniciándose repetidamente.
- `/readyz` fuera de servicio.
- Crecimiento anormal de `audit_events`.
- Dispositivos inesperadamente offline.
- Cambios de clave pública de RustDesk.
- Fallos repetidos de login.

## Limpieza

Los eventos de auditoría no tienen eliminación automática en 1.0. Para uso personal su volumen es bajo. Antes de agregar una política de retención, conservar evidencia suficiente para investigar accesos.
