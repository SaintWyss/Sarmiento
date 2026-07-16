# 06 — Seguridad, pruebas y calidad

## Activos que protejo

- cuenta del owner;
- MFA y códigos de recuperación;
- credenciales de dispositivos;
- inventario y presencia;
- IDs y claves de RustDesk;
- control de teclado, mouse y pantalla;
- auditoría;
- backups;
- configuración de Deskflow y unidades locales.

## Límites de confianza

Yo separo:

- navegador/PWA;
- aplicación desktop;
- API pública;
- agentes;
- PostgreSQL;
- servicios RustDesk;
- red LAN/Internet;
- procesos locales Deskflow/RustDesk.

Un agente autenticado no equivale al owner. Un deep link no equivale a una orden administrativa. Un dispositivo online no equivale a una sesión remota autorizada.

## Amenazas principales

| Amenaza | Ejemplo | Control |
|---|---|---|
| robo de owner | contraseña filtrada | MFA, lockout y sesión segura |
| replay de enrolamiento | reutilizar token | token de un solo uso + lock transaccional |
| fuga de DB | obtener credenciales | hashes/HMAC y cifrado de secretos sensibles |
| rotación destructiva | revocar antes de persistir | protocolo pending→promote |
| agente malicioso | metadata enorme/falsa | límites, validación y permisos mínimos |
| ID RustDesk inyectado | argumentos maliciosos | formato allowlist y spawn sin shell |
| deep link abusivo | URL ejecuta comando | esquema y acciones cerradas |
| CSRF | operación desde sitio ajeno | token CSRF + cookies adecuadas |
| fuerza bruta | login repetido | rate limit y lockout persistente |
| exposición pública | hosts/orígenes amplios | Caddy, TLS, trusted hosts y CORS |
| supply chain | imagen/agente comprometido | versiones fijadas, CI y auditoría |
| pérdida de acceso | claves RustDesk/DB perdidas | backups y restore drills |

## Controles implementados

- MFA TOTP;
- recovery codes de un solo uso;
- lockout persistente;
- JWT con issuer, audience y claims obligatorios;
- cookies seguras y CSRF;
- límites de body y metadata;
- rate limiter acotado;
- enrolamiento serializado;
- credenciales almacenadas de forma no reversible;
- rotación tolerante a fallos;
- API `no-store` para datos sensibles;
- validación de IDs RustDesk;
- CSP cerrada en desktop;
- frontend sin shell general;
- HTTPS obligatorio salvo localhost controlado;
- auditoría de acciones;
- workflows de seguridad/dependencias.

## Riesgos residuales

- rate limiting distribuido puede ser necesario en despliegues con múltiples réplicas;
- permisos de captura/input dependen del OS;
- Wayland y portales varían;
- una LAN comprometida afecta Deskflow si su configuración no está protegida;
- companion/deep link amplía la superficie local;
- recuperación total depende de backups de DB y claves RustDesk;
- alertas y retención de auditoría deben formalizarse;
- la aplicación desktop se valida principalmente en Linux/KDE.

## Pruebas backend

Yo verifico:

- login, MFA, recovery y lockout;
- enrolamiento único y carreras;
- heartbeat y presencia;
- autorización del owner;
- rotación con respuestas perdidas;
- promoción de credencial pendiente;
- revocación;
- auditoría;
- migraciones;
- límites de payload;
- headers y configuración segura.

Comandos exactos dependen del proyecto, pero incluyen pytest, Ruff, compilación y Alembic.

## Pruebas de agentes

Por sistema operativo:

- instalación como servicio;
- permisos del archivo secreto;
- enrolamiento;
- heartbeat;
- reconexión;
- rotación;
- upgrade/rollback;
- desinstalación;
- logs sin credenciales.

Los scripts Shell y PowerShell pasan validación sintáctica y tests específicos cuando existen.

## Pruebas PWA/companion

- sintaxis/build frontend;
- auth/CSRF;
- inventario;
- deep links;
- validación de payload;
- caché/service worker;
- comportamiento móvil;
- errores cuando el companion no está instalado.

## Pruebas desktop

```bash
npm ci
npm run build
cargo test --all-targets
cargo clippy --all-targets -- -D warnings
```

También verifico:

- comandos Tauri allowlisted;
- CSP/capabilities;
- sesión en memoria;
- bandeja y autostart;
- deep link;
- lanzamiento RustDesk;
- rollback Deskflow;
- AppImage/instalador.

## Smoke físico

CI no puede demostrar:

- captura real de pantalla;
- control de teclado/mouse;
- permisos de accesibilidad;
- Wayland/X11;
- múltiples monitores;
- NAT/relay;
- comportamiento de Deskflow entre dos máquinas.

Yo registro una matriz por equipo, OS, sesión, versión, red y resultado.

## Gates de release

1. pruebas backend;
2. migración desde versión soportada;
3. build de contenedores;
4. lint de scripts;
5. build/test desktop;
6. seguridad/dependencias;
7. backup/restore;
8. smoke LAN;
9. smoke RustDesk externo/relay;
10. smoke Deskflow físico;
11. documentación y rollback.

## Calidad arquitectónica

Yo verifico que:

- routers no concentren lógica de negocio;
- agentes no reciban privilegios del owner;
- migraciones sean la autoridad del esquema;
- secretos no se registren;
- la rotación sea idempotente;
- las acciones locales sean cerradas;
- cada fallo restaure Deskflow cuando corresponda;
- la app no persista sesión accidentalmente.

## Supply chain

- imágenes y versiones fijadas;
- dependabot/auditoría;
- SBOM y checksums para releases;
- AppImage desde CI controlado;
- scripts descargados por HTTPS y verificados;
- secret scanning;
- claves de firma fuera del repositorio.

## Definición de terminado

Yo considero terminada una función cuando tiene implementación, autorización, prueba automatizada, smoke físico si toca hardware, auditoría, documentación, error accionable y rollback.