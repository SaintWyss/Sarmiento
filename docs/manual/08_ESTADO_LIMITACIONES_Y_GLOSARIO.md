# 08 — Estado, limitaciones, roadmap y glosario

## Estado actual

| Capacidad | Estado |
|---|---|
| control-plane FastAPI/PostgreSQL | implementado |
| autenticación owner | implementada |
| MFA/recovery/lockout | implementados |
| enrolamiento de un solo uso | implementado y endurecido |
| agentes Linux/Windows/macOS | implementados; aceptación varía por OS |
| heartbeat/presencia | implementados |
| rotación tolerante a fallos | implementada |
| revocación, alias y etiquetas | implementados |
| auditoría | implementada |
| PWA | implementada |
| companion y `sarmiento://` | implementados |
| RustDesk server propio | implementado |
| modos gráficos Deskflow/RustDesk | implementados |
| aplicación Tauri Linux | implementada |
| AppImage/instalador | implementados |
| bandeja/autostart | implementados |
| aceptación KDE/X11 | principal entorno validado |
| Wayland y otros OS desktop | aceptación parcial/externa |
| NAT/firewall/relay | depende del entorno real |
| monitoreo avanzado/retención | ampliable |

## Limitaciones conocidas

- la aplicación nativa principal está orientada a Linux;
- Deskflow depende de configuración y unidades concretas;
- Wayland puede restringir captura, foco e input;
- permisos de macOS/Windows requieren aceptación local;
- NAT y firewall no se resuelven solo desde el repositorio;
- la PWA necesita companion para lanzar el cliente local;
- la sesión desktop no persiste por decisión de seguridad;
- el servidor RustDesk y los clientes deben mantener compatibilidad;
- los volúmenes/keys de RustDesk son críticos para continuidad;
- una rotación puede permanecer pendiente mientras el equipo está offline;
- múltiples archivos `.env` pueden provocar despliegues incoherentes;
- CI no reemplaza pruebas de pantalla, teclado, mouse y monitores reales.

## Roadmap recomendado

### 1. Operación y observabilidad

- métricas y alertas integradas;
- dashboard de rotaciones/heartbeats;
- política de retención de auditoría;
- restore drills programados;
- health detallado de RustDesk;
- diagnóstico guiado de red.

### 2. Compatibilidad

- matriz Linux/KDE/GNOME/X11/Wayland;
- aceptación Windows/macOS de agentes;
- instaladores firmados;
- upgrades automáticos controlados;
- detección de versiones incompatibles.

### 3. Seguridad

- secret manager;
- rate limiting distribuido si escala;
- firma y verificación de agentes/desktop;
- SBOM;
- políticas de rotación periódica;
- hardening del companion/deep link;
- alertas de identidad RustDesk cambiada.

### 4. Producto

- onboarding de estación;
- editor visual de disposición Deskflow;
- diagnóstico de permisos;
- historial de sesiones remotas;
- recuperación guiada;
- mejor UX móvil;
- perfiles de conexión por red/equipo.

## Glosario

**Control-plane:** servicio que administra identidad, dispositivos, permisos y estado.

**Agente:** proceso instalado en un equipo que se enrola y envía heartbeats.

**Enrolamiento:** registro inicial seguro de un dispositivo.

**Token de un solo uso:** secreto temporal que solo puede consumirse una vez.

**Heartbeat:** mensaje periódico que indica que un agente sigue disponible.

**Presencia:** estado online/offline derivado del último heartbeat.

**Rotación:** reemplazo controlado de una credencial.

**Credencial pendiente:** secreto nuevo que todavía no desplazó al anterior.

**Promoción:** momento en que el primer uso válido de la nueva credencial la convierte en actual.

**Revocación:** anulación de acceso de un dispositivo o sesión.

**HMAC:** mecanismo criptográfico usado para verificar un secreto sin almacenarlo directamente.

**MFA:** autenticación con más de un factor.

**TOTP:** código temporal generado por una app autenticadora.

**Recovery code:** código de emergencia de un solo uso.

**Lockout:** bloqueo temporal/persistente después de intentos fallidos.

**CSRF:** ataque que intenta ejecutar una acción autenticada desde otro sitio.

**PWA:** aplicación web instalable.

**Tauri:** framework para aplicación nativa con UI web y backend Rust.

**Companion:** programa local que recibe una acción limitada desde la PWA.

**Deep link:** URL con esquema propio, como `sarmiento://`, asociada a una app.

**RustDesk:** software de escritorio remoto usado para imagen e input.

**hbbs:** servidor de rendezvous/ID de RustDesk.

**hbbr:** servidor relay de RustDesk.

**Deskflow:** software para compartir teclado y mouse entre equipos.

**Pantallas físicas:** modo en el que Deskflow conecta la estación sin transmitir video.

**Abrir en monitor:** modo que pausa Deskflow y abre RustDesk para ver/controlar el equipo.

**Rollback:** restauración del estado o versión anterior.

**Caddy:** reverse proxy usado para HTTPS.

**Alembic:** herramienta de migraciones de base de datos.

**AppImage:** paquete portátil de aplicación Linux.

**X11/Wayland:** sistemas/protocolos de sesión gráfica de Linux.

**NAT:** traducción de direcciones de red que afecta conexiones externas.

**Relay:** servidor intermedio cuando los clientes no pueden conectarse directamente.

**RPO/RTO:** pérdida máxima de datos y tiempo objetivo de recuperación.

## Cierre

Yo considero Sarmiento una plataforma funcional y operable para mi estación, con una aplicación nativa real y un control-plane seguro. Mantengo explícito que la aceptación de pantalla/input, Wayland, firewall, NAT y hardware pertenece al entorno real y no puede declararse completa solo porque CI esté verde.