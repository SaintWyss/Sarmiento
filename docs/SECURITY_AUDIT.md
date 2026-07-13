# Auditoría de seguridad — Sarmiento 1.1

Fecha de revisión: 2026-07-12. Alcance: código de `main` posterior a 1.0.1, infraestructura Docker, agentes, frontend y documentación.

## Resultado ejecutivo

La base 1.0.1 ya tenía buenas decisiones: separación del plano de datos, no almacenamiento de contraseñas RustDesk, tokens HMAC, CSRF, cookies HttpOnly, CSP, API privada y rotación tolerante a fallos. La revisión 1.1 cerró los principales huecos del panel expuesto a Internet.

| Severidad inicial | Hallazgo | Estado 1.1 |
|---|---|---|
| Alta | Cuenta administrativa sin segundo factor | Corregido: TOTP + recovery codes |
| Alta | Body/metadata de agente sin límite global | Corregido: límite ASGI + 16 KiB metadata |
| Media | Lockout solo dependía del rate limit en memoria | Corregido: contador y bloqueo persistentes |
| Media | JWT sin `iss`, `aud` ni claims obligatorios | Corregido |
| Media | Buckets del rate limiter podían crecer sin límite | Corregido: límite y poda |
| Media | Cookies sin prefijo de host en producción | Corregido: `__Host-` |
| Baja | Respuestas API autenticadas podían cachearse | Corregido: `Cache-Control: no-store` |
| Baja | Alias con espacios podía superar validación previa | Corregido: normalización no vacía |
| Alta | Carrera al consumir token de enrolamiento | Corregido en 1.0.1 con lock de fila |
| Alta | Rotación podía cortar al agente por pérdida de respuesta | Corregido en 1.0.1 con promoción en dos fases |

## Revisión por área

### Autenticación

- Contraseñas con scrypt, sal aleatoria y comparación constante.
- Hash ficticio para reducir enumeración por tiempo.
- MFA TOTP compatible con RFC 6238; SHA-1 se usa únicamente porque es el algoritmo interoperable estándar de TOTP.
- Se bloquea el replay del mismo período TOTP.
- Códigos de recuperación de un uso; solo se persiste HMAC.
- El secreto MFA se cifra con Fernet usando una clave derivada del pepper estable.
- Cambio de contraseña, habilitación y deshabilitación de MFA incrementan `session_version` e invalidan sesiones.

### Sesiones y navegador

- JWT HS256 exige emisor, audiencia, expiración, `nbf`, `jti`, tipo y versión de sesión.
- Cookie de sesión HttpOnly, Secure, SameSite Strict y `__Host-` en producción.
- CSRF double-submit para mutaciones.
- CSP estricta, frame deny, HSTS y no-sniff en Caddy.
- Respuestas `/api/` marcadas `no-store`.

### Agentes

- Credencial individual, revocable y rotación automática de dos fases.
- Inventario limitado por esquema y tamaño.
- El agente no acepta ni ejecuta comandos arbitrarios desde el servidor.
- Comprometer un agente no entrega automáticamente la contraseña RustDesk desde Sarmiento, porque no se almacena allí.

### Infraestructura

- API y PostgreSQL no exponen puertos al host.
- Contenedores y clientes usan versiones fijas, no `latest`.
- API corre como usuario no root.
- Alembic es la autoridad del esquema en producción.
- CI valida pruebas, lint, sintaxis, migraciones, Compose e imagen.
- Workflow semanal ejecuta `pip-audit` y Bandit.

## Riesgos residuales aceptados

1. **Aceptación física pendiente:** permisos de pantalla/input, Wayland, firewall y deep links requieren prueba en hardware real.
2. **Rate limit local:** suficiente para una instancia; no coordina varios workers. Redis es requisito antes de escalar horizontalmente.
3. **Supply chain de RustDesk:** versiones fijadas y HTTPS, pero los instaladores no verifican una firma/digest oficial estable.
4. **Tags Docker sin digest:** evitan `latest`, pero un tag remoto todavía puede ser reemplazado. Producción de mayor criticidad debe pinnear `@sha256`.
5. **Host comprometido:** root/Administrator puede leer el token local del agente y la configuración de RustDesk.
6. **Autorización del canal remoto:** Sarmiento inventaría y abre el viewer; RustDesk y la contraseña permanente autorizan la sesión real.
7. **Auditoría mutable:** un administrador de PostgreSQL puede alterar eventos. Para no repudio fuerte se requiere exportación append-only externa.

## Recomendaciones operativas

- Activar MFA inmediatamente después del primer login.
- No publicar `api:8000` ni PostgreSQL.
- Usar dominio y TLS válido; limitar firewall.
- Guardar contraseñas RustDesk y recovery codes en un gestor de contraseñas.
- Ejecutar backup/restore y el checklist de aceptación después de cada upgrade mayor.
- Revisar Dependabot y el workflow Security semanalmente.
