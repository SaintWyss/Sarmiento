# Modelo de amenazas de Sarmiento 1.1

## Alcance

El análisis cubre el panel web, API, base de datos, agentes, instaladores, Caddy y servidores RustDesk. El protocolo interno de RustDesk se trata como dependencia externa; Sarmiento no modifica su criptografía ni su canal de media.

## Activos

- Cuenta y sesión del propietario.
- Secretos MFA y códigos de recuperación.
- Tokens temporales de enrolamiento.
- Tokens persistentes de agentes.
- Clave privada del servidor RustDesk.
- Contraseña permanente guardada en cada host.
- Inventario, IPs y auditoría.
- Disponibilidad de hbbs/hbbr y del control-plane.

## Fronteras de confianza

1. Internet → Caddy/hbbs/hbbr.
2. Caddy → API en red Docker privada.
3. API → PostgreSQL.
4. Host local → archivo de configuración del agente.
5. Navegador → handler local `sarmiento://` → RustDesk viewer.
6. Instalador privilegiado → artefactos descargados.

## STRIDE

| Amenaza | Ejemplo | Control actual | Riesgo residual |
|---|---|---|---|
| Spoofing | Robo de contraseña del owner | scrypt, MFA TOTP, recovery de un uso, lockout, rate limit | Phishing y malware del navegador |
| Spoofing | Agente falso usa token robado | token por dispositivo, hash con pepper, rotación/revocación | Compromiso root/admin del host |
| Tampering | Reuso concurrente de token de enroll | TTL, uso único, `SELECT FOR UPDATE` | SQLite de desarrollo no replica locks de PostgreSQL |
| Tampering | Modificar inventario arbitrario | autenticación por agente, límites JSON | Un host comprometido puede mentir sobre sí mismo |
| Repudiation | Negar login o revocación | auditoría con actor, IP, destino y fecha | Administrador del DB puede alterar registros |
| Information disclosure | Filtrar contraseñas RustDesk | nunca se envían ni persisten centralmente | Se muestran una vez en el instalador y viven en el host |
| Information disclosure | Robo de tokens desde DB | solo HMAC; pepper separado | Robo simultáneo de DB + env permite ataque offline |
| DoS | Bodies o metadata enormes | límite ASGI y límite JSON | Flood volumétrico debe mitigarse en firewall/CDN |
| DoS | Muchas IPs llenan rate limiter | buckets acotados y limpieza | Rate limit es local a una instancia |
| Elevation | CSRF administrativo | SameSite Strict + double-submit CSRF | XSS del mismo origen rompería la barrera; CSP reduce riesgo |
| Elevation | Deep link malicioso | handler valida formato de RustDesk ID | Vulnerabilidad futura del cliente RustDesk |

## Escenarios de abuso prioritarios

### Fuerza bruta del propietario

El atacante combina credenciales filtradas con intentos distribuidos. Caddy entrega la IP real al API; existe límite por IP y lockout persistente por cuenta. MFA detiene el uso de una contraseña aislada. Un ataque distribuido todavía puede provocar lockout intencional, por lo que el evento queda auditado.

### Robo del token del agente

El atacante puede falsificar heartbeat e inventario del dispositivo, pero no obtiene la contraseña de RustDesk ni una sesión remota. La respuesta es revocar el dispositivo, limpiar el archivo local, enrolarlo otra vez y rotar el pepper únicamente ante compromiso masivo.

### Compromiso del servidor

Acceso root al VPS permite leer variables, DB y clave privada RustDesk. Deben restaurarse desde un host limpio, rotarse session secret y pepper, regenerarse identidad RustDesk, revocarse todos los agentes y cambiar contraseñas permanentes de hosts.

### Supply chain del instalador

Los instaladores ejecutan con privilegios y descargan RustDesk y scripts. Se fijan versiones, se usa HTTPS y no se usa `latest`, pero todavía no se valida una firma o digest oficial del binario RustDesk. Es un riesgo residual explícito hasta disponer de digests verificables y estables.

## Requisitos de despliegue seguro

- API sin publicación directa de puertos.
- HTTPS real; no usar producción pública con `http://`.
- Firewall limitado a 80/443 y puertos RustDesk necesarios.
- `infra/.env` modo `0600`, fuera de backups sin cifrar.
- MFA activado antes de exponer el panel.
- Backups cifrados y prueba de restauración.
- Actualizaciones mediante PR y CI; no editar contenedores en vivo.
- Alertas externas para disponibilidad y eventos de login bloqueado.
