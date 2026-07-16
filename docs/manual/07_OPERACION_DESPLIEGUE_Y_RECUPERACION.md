# 07 — Operación, despliegue y recuperación

## Entornos

Yo separo:

- desarrollo local;
- staging con equipos de prueba;
- producción LAN o VPS;
- estaciones físicas del owner.

No uso la base productiva para pruebas de enrolamiento destructivas ni regenero secretos porque un entorno local “no arranca”.

## Despliegue del servidor

Flujo recomendado:

1. fijar versión/commit;
2. crear y proteger el archivo de entorno activo;
3. verificar que no exista otro `.env` consumido por el despliegue;
4. respaldar PostgreSQL y volúmenes RustDesk;
5. validar Docker Compose;
6. ejecutar migraciones;
7. levantar servicios;
8. comprobar health;
9. probar login/MFA;
10. comprobar heartbeat de un agente de prueba;
11. probar RustDesk y relay;
12. habilitar acceso normal.

```bash
docker compose config
docker compose up -d --build
docker compose ps
docker compose logs --tail=200 api
```

Los nombres exactos de servicios se toman del Compose vigente.

## Orden de dependencias

```text
PostgreSQL → migraciones → API → Caddy → agentes/PWA/desktop
RustDesk hbbs/hbbr → clientes RustDesk
```

Yo no inicio múltiples réplicas API ejecutando migraciones concurrentes.

## Health y smoke

Verifico:

- HTTPS válido;
- endpoint health;
- conexión DB;
- esquema Alembic esperado;
- login y MFA;
- inventario;
- creación/consumo de token de prueba;
- heartbeat;
- auditoría;
- puertos RustDesk;
- deep link/desktop.

## Backup del control-plane

```bash
mkdir -p backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose exec -T postgres \
  pg_dump -U <usuario> -d <base> -Fc \
  > "backups/sarmiento-${stamp}.dump"
sha256sum "backups/sarmiento-${stamp}.dump" \
  > "backups/sarmiento-${stamp}.dump.sha256"
chmod 600 backups/sarmiento-${stamp}.dump*
```

Yo reemplazo placeholders según el entorno y nunca copio una contraseña al comando si quedará en historial.

## Backup de RustDesk

Respaldo el volumen/directorio que conserva:

- claves del servidor;
- ID/identidad;
- configuración persistente necesaria.

Cambio de esas claves puede hacer que los clientes vean otro servidor o requieran reconfiguración.

## Backup de configuración

Incluyo:

- Compose y overrides;
- archivo de entorno cifrado o referencias a secret manager;
- configuración Caddy;
- scripts de agentes/versiones;
- unidades Deskflow conocidas;
- instaladores desktop;
- inventario de versiones.

No incluyo secretos sin cifrado.

## Restore drill

1. crear servidor aislado;
2. verificar checksums;
3. restaurar PostgreSQL;
4. restaurar identidad RustDesk;
5. ejecutar Alembic hasta la revisión esperada;
6. iniciar servicios con hostname de prueba;
7. verificar owner/MFA mediante procedimiento controlado;
8. conectar un agente sintético;
9. comprobar rotación;
10. probar RustDesk sin afectar equipos reales;
11. registrar RPO/RTO.

## Upgrade

1. leer changelog y migraciones;
2. crear backups;
3. actualizar imágenes/código por versión inmutable;
4. ejecutar CI local aplicable;
5. migrar;
6. smoke;
7. actualizar un agente canario;
8. actualizar desktop canario;
9. validar hardware;
10. desplegar gradualmente.

## Rollback

- revertir imagen/código a versión compatible;
- no bajar esquema destructivamente sin plan;
- conservar las credenciales nuevas si la versión anterior puede validarlas;
- no restaurar una base vieja sin reconciliar dispositivos enrolados después;
- preferir forward-fix si hubo escrituras incompatibles;
- probar owner, heartbeat, rotación y RustDesk.

## Incidente de credenciales del owner

1. bloquear acceso externo si es necesario;
2. rotar contraseña y secretos de sesión;
3. revisar MFA/recovery usados;
4. invalidar sesiones;
5. revisar auditoría de enrolamiento, rotación y revocación;
6. rotar secretos de infraestructura afectados;
7. evaluar notificación;
8. documentar causa raíz.

## Incidente de agente comprometido

1. revocar dispositivo en control-plane;
2. rotar credencial si el equipo sigue bajo control;
3. retirar acceso RustDesk/Deskflow;
4. revisar heartbeats y metadata;
5. buscar acciones del dispositivo;
6. reinstalar agente desde artefacto verificado;
7. reenrolar con token nuevo;
8. no reutilizar la credencial anterior.

## Rotación atascada

- no revocar manualmente la credencial vieja sin confirmar el estado del agente;
- revisar logs del heartbeat;
- comprobar escritura del secreto en el OS;
- reintentar de forma idempotente;
- cancelar/reiniciar la rotación mediante el procedimiento soportado;
- auditar la intervención.

## Incidente RustDesk

- verificar procesos `hbbs`/`hbbr`;
- revisar puertos, firewall y NAT;
- comprobar identidad/key del servidor;
- probar conexión LAN y relay por separado;
- no regenerar volúmenes antes de respaldarlos;
- comprobar versión cliente-servidor;
- preservar logs sin contraseñas.

## Incidente Deskflow

1. identificar server/client;
2. consultar `systemctl --user status`;
3. verificar red y configuración de pantallas;
4. restaurar estado previo desde la app o manualmente;
5. probar teclado/mouse local;
6. revisar permisos de sesión gráfica;
7. registrar el cambio.

## Aplicación desktop

Para actualizar/desinstalar:

- cerrar app y bandeja;
- respaldar preferencias no sensibles;
- instalar AppImage/paquete de la misma release;
- verificar desktop entry y deep link;
- probar login;
- probar Deskflow y RustDesk;
- conservar el artefacto anterior.

## Observabilidad y alertas

Yo alerto por:

- API/DB/RustDesk caídos;
- certificados próximos a vencer;
- login/lockout anormal;
- heartbeats vencidos;
- rotaciones pendientes demasiado tiempo;
- enrolamientos inusuales;
- errores de auditoría;
- espacio en volúmenes/backups;
- cambios de identidad RustDesk;
- fallos repetidos del companion/desktop.

## Evidencia mínima de incidente

- timestamp UTC;
- versión de cada componente;
- entorno/red;
- owner/device IDs internos;
- request/audit IDs;
- estado de rotación;
- servicios afectados;
- logs sanitizados;
- acciones de contención;
- recuperación y verificación;
- responsable.