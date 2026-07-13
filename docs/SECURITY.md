# Seguridad

## Activos protegidos

- Acceso administrativo al panel.
- Tokens de enrolamiento.
- Credenciales de agentes.
- Identidad privada del servidor RustDesk.
- Contraseña permanente configurada en cada host.

## Controles

- Contraseñas de propietario derivadas con scrypt y salt aleatorio.
- Sesiones JWT HS256 en cookie HttpOnly, SameSite=Strict y Secure en producción.
- Protección CSRF por double-submit cookie.
- Rate limiting separado para login y API general.
- Tokens aleatorios de alta entropía.
- Tokens de enrolamiento de uso único y TTL corto.
- Credenciales de agentes independientes y revocables.
- HMAC-SHA-256 con pepper para tokens persistidos.
- HTTPS y headers de seguridad por Caddy.
- CSP sin scripts externos ni `unsafe-inline`.
- API no publicada directamente por Docker.
- Clave privada RustDesk fuera del repositorio.
- Auditoría de login, enrolamiento y cambios administrativos.

## Lo que Sarmiento no almacena

- Contraseña permanente de RustDesk.
- Video o audio de sesiones.
- Pulsaciones de teclado.
- Archivos transferidos.
- Contenido de portapapeles.

## Rotación

- Propietario: usar **Seguridad → Cambiar contraseña** en el panel. La operación incrementa la versión de sesión e invalida de inmediato todas las sesiones existentes. `SARMIENTO_OWNER_PASSWORD` solo define la contraseña del primer arranque.
- Sesiones: cambiar `SARMIENTO_SESSION_SECRET`; invalida sesiones existentes.
- Tokens: cambiar `SARMIENTO_TOKEN_PEPPER` invalida tokens de agentes y enrolamiento, por lo que todos deben volver a enrolarse.
- Agente individual: usar **Rotar credencial**, copiar el nuevo token y ejecutar el comando de reemplazo en el host.

Linux:

```bash
sudo python3 /opt/sarmiento/sarmiento_agent.py replace-token 'sat_...'
sudo systemctl restart sarmiento-agent
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:ProgramData\Sarmiento\sarmiento-agent.ps1" -Mode ReplaceToken -NewToken 'sat_...'
Restart-ScheduledTask -TaskName SarmientoAgent
```

## Reporte de vulnerabilidades

No publiques credenciales, claves, IP privadas o capturas del panel en un issue público. Revocá primero cualquier secreto expuesto y luego documentá el incidente sin incluir el valor comprometido.

## Rotación de credenciales del agente

El propietario solicita la rotación desde el panel. El agente autenticado recibe la señal en el siguiente heartbeat, intercambia su credencial por una nueva y la persiste localmente con permisos restringidos. La credencial anterior deja de ser válida únicamente después de que el agente recibe y guarda la nueva.
