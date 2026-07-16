# 02 — Uso funcional

## Inicio de sesión

Yo accedo con owner, contraseña y MFA cuando está habilitado. La sesión web usa cookies seguras y CSRF; la aplicación nativa conserva sesión en memoria y no la persiste como un secreto reutilizable en disco.

## Inventario

Cada dispositivo muestra información como:

- alias;
- sistema operativo;
- estado online/offline;
- último heartbeat;
- ID RustDesk;
- etiquetas;
- versión de agente;
- estado de credencial/rotación;
- acciones permitidas.

Yo no uso solo el nombre del host como identidad. El ID interno y la credencial del agente son la autoridad.

## Enrolamiento

Flujo:

1. owner crea un token de un solo uso;
2. agente envía metadata limitada;
3. servidor consume el token de forma serializada;
4. emite una credencial del dispositivo;
5. agente la guarda con permisos adecuados;
6. comienza heartbeat;
7. inventario refleja presencia.

Un token consumido no debe reutilizarse aunque dos solicitudes lleguen simultáneamente.

## Heartbeat

El agente informa presencia y puede recibir instrucciones de control-plane, como una rotación pendiente.

Yo limito tamaño y campos de metadata para evitar abuso o almacenamiento arbitrario.

## Rotación de credenciales

La rotación está diseñada para tolerar respuestas perdidas:

1. owner solicita rotación;
2. servidor marca estado pendiente;
3. heartbeat informa al agente;
4. agente solicita la nueva credencial;
5. credencial anterior sigue válida temporalmente;
6. agente persiste la nueva;
7. primer heartbeat con la nueva la promueve;
8. servidor revoca la anterior.

Yo evito revocar primero porque podría dejar una máquina inaccesible si la respuesta se pierde.

## Revocar un equipo

La revocación impide nuevos heartbeats y acciones de administración. También debo revisar RustDesk/Deskflow si la máquina ya no es confiable.

## Modo “Pantallas físicas”

Este modo reanuda la configuración de Deskflow para compartir teclado y mouse entre la PC principal y la notebook.

La app solo controla unidades conocidas y no permite ejecutar shell arbitrario desde el frontend.

Verifico:

- server/client correctos;
- dirección/IP;
- posición de pantallas;
- servicios activos;
- input real;
- rollback.

## Modo “Abrir en monitor”

Este modo:

1. guarda el estado relevante de Deskflow;
2. pausa Deskflow para evitar conflicto de input;
3. valida el ID RustDesk;
4. abre RustDesk;
5. permite restaurar Deskflow al cerrar o ante fallo.

Yo no concateno el ID en una shell libre. Uso una allowlist de formato y argumentos separados.

## RustDesk 1-click

El protocolo `sarmiento://` o el cliente nativo recibe una acción validada. El handler debe:

- reconocer solo acciones soportadas;
- validar identificadores;
- no aceptar comandos arbitrarios;
- localizar RustDesk de forma controlada;
- registrar el resultado;
- mostrar errores accionables.

## Aplicación nativa

La app Tauri permite:

- login/MFA;
- cambio de contraseña;
- inventario;
- enrolamiento;
- auditoría;
- acciones por dispositivo;
- Deskflow;
- RustDesk;
- bandeja;
- autostart;
- deep link.

Yo uso la aplicación nativa como interfaz principal de PC porque se integra mejor con procesos y bandeja que una web.

## Panel web/PWA

La PWA sirve para:

- consultar inventario;
- administrar dispositivos;
- usar desde teléfono;
- conexión 1-click mediante companion;
- contingencia cuando la app nativa no está disponible.

No tiene permiso para ejecutar cualquier programa local; depende del companion/handler registrado.

## Auditoría

Yo reviso eventos de:

- login y lockout;
- enrolamiento;
- rotación;
- revocación;
- alias/etiquetas;
- acciones de conexión;
- cambios de contraseña/MFA;
- errores importantes.

## MFA y recuperación

Los códigos de recuperación son de un solo uso. Yo los guardo fuera del servidor. Si pierdo TOTP y códigos, necesito el procedimiento de recuperación documentado, no desactivar controles directamente en la base sin registro.

## Errores frecuentes

| Síntoma | Causa probable | Acción |
|---|---|---|
| equipo offline | agente caído/red/credencial | revisar servicio y logs del agente |
| RustDesk no abre | cliente/path/ID/protocolo | probar cliente y handler separados |
| Deskflow no comparte input | unidades/config/firewall | revisar `systemctl --user` y red |
| app no inicia sesión | TLS, cookie, credenciales, MFA | revisar URL y logs sanitizados |
| rotación queda pendiente | agente offline o no persistió | mantener credencial vieja y diagnosticar |
| deep link no funciona | registro XDG/handler | reinstalar asociación y probar URL |
| Wayland bloquea control | permisos/compositor | usar flujo soportado o configurar portal/permisos |
| múltiples `.env` | despliegue usa archivo distinto | identificar fuente única antes de recrear stack |

## Regla operativa

Yo nunca resuelvo un problema de conexión deshabilitando TLS, MFA o validación de IDs de forma permanente. Primero separo servidor, agente, RustDesk, Deskflow y app para identificar qué capa falla.