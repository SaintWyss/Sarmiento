# Seguridad

## Activos protegidos

- Acceso administrativo al panel.
- Secreto TOTP y códigos de recuperación.
- Tokens de enrolamiento y credenciales de agentes.
- Identidad privada del servidor RustDesk.
- Contraseña permanente configurada en cada host.
- Inventario, IPs y auditoría.

## Controles

- Contraseñas del propietario con scrypt y sal aleatoria.
- MFA TOTP opcional, recomendado en producción, con anti-replay y recovery codes de un uso.
- Secreto MFA cifrado; recovery codes y tokens persistidos únicamente como HMAC.
- Lockout persistente de cuenta más rate limit por IP.
- JWT con emisor, audiencia, expiración, `nbf`, `jti` y versión de sesión obligatorios.
- Cookies HttpOnly/Secure/SameSite Strict; prefijo `__Host-` bajo HTTPS.
- Protección CSRF por double-submit cookie.
- Tokens de enrolamiento de un uso, TTL corto y consumo serializado con lock de fila.
- Credenciales por agente, revocables y rotación automática tolerante a reintentos.
- Límite global del body HTTP y límite específico de metadata.
- HTTPS, CSP, HSTS y headers de seguridad por Caddy.
- API y PostgreSQL sin puertos publicados por Docker.
- Clave privada RustDesk fuera del repositorio.
- Auditoría de login, MFA, enrolamiento, rotación y administración.
- CI, `pip-audit` y Bandit.

## Activar MFA

Abrí **Seguridad → Activar autenticación en dos pasos**. Cargá la clave en una aplicación TOTP, validá un código y guardá los códigos de recuperación en un gestor de contraseñas. Habilitar MFA invalida la sesión actual para obligar a probar el nuevo factor.

## Lo que Sarmiento no almacena

- Contraseña permanente de RustDesk.
- Video o audio de sesiones.
- Pulsaciones de teclado.
- Archivos transferidos.
- Contenido de portapapeles.

## Rotación e incidentes

- **Contraseña:** cambiarla en el panel invalida todas las sesiones.
- **Sesiones:** cambiar `SARMIENTO_SESSION_SECRET` invalida todas las sesiones.
- **Tokens:** cambiar `SARMIENTO_TOKEN_PEPPER` invalida agentes, tokens de enrolamiento y cifrado MFA; requiere re-enrolar y reconfigurar MFA.
- **Agente individual:** solicitar rotación desde el panel; el agente la completa en el próximo heartbeat sin cortar primero la credencial anterior.
- **Servidor comprometido:** regenerar identidad RustDesk, session secret, pepper, contraseña del owner y contraseñas permanentes de hosts desde un entorno limpio.

## Confianza en proxy

El despliegue oficial permite proxy headers porque el API solo es accesible desde Caddy en la red Docker privada. No publiques el puerto 8000. Si cambiás la topología, restringí `SARMIENTO_FORWARDED_ALLOW_IPS` a proxies concretos.

## Reporte de vulnerabilidades

No publiques credenciales, claves, IP privadas o capturas del panel en un issue público. Revocá primero cualquier secreto expuesto y luego documentá el incidente sin incluir el valor comprometido. Consultá también [`THREAT_MODEL.md`](THREAT_MODEL.md) y [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md).
