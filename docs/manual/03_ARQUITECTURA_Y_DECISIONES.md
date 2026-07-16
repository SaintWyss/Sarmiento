# 03 — Arquitectura y decisiones de ingeniería

## Explicación simple

Yo diseñé Sarmiento como una plataforma compuesta por varias piezas especializadas. No intenté convertir RustDesk, Deskflow, inventario, autenticación y UI en un único programa monolítico imposible de mantener.

Cada pieza resuelve una responsabilidad:

- el **control-plane** conoce usuarios, equipos, estados y permisos;
- los **agentes** informan presencia y reciben rotaciones;
- **RustDesk** transporta imagen, teclado y mouse para una sesión remota;
- **Deskflow** comparte teclado y mouse entre equipos cercanos;
- la **aplicación nativa** coordina la experiencia de escritorio;
- la **PWA** permite administración desde navegador o teléfono.

## Analogía

Pienso Sarmiento como un aeropuerto:

- el control-plane es la torre de control;
- los agentes son las aeronaves que reportan posición;
- RustDesk es el canal para entrar a una cabina remota;
- Deskflow es una pasarela física entre terminales cercanas;
- la app nativa es el tablero del operador;
- la auditoría es la caja negra.

## Estilo arquitectónico

Yo uso una arquitectura modular con ports/adapters en el backend y clientes separados por plataforma.

```text
clientes → API/control-plane → casos de uso → dominio → repositorios/adaptadores
```

RustDesk y Deskflow se integran como sistemas externos; Sarmiento no reimplementa sus protocolos de streaming o captura.

## Componentes y responsabilidades

| Componente | Responsabilidad |
|---|---|
| FastAPI control-plane | autenticación, inventario, enrolamiento, rotación, auditoría y API |
| PostgreSQL | estado durable, locks y relaciones |
| Alembic | evolución controlada del esquema |
| Caddy | TLS y reverse proxy |
| `hbbs`/`hbbr` | rendezvous y relay de RustDesk |
| agentes | enrolamiento, heartbeat, metadata y rotación |
| PWA | administración y acceso móvil |
| companion/deep link | puente seguro entre navegador y cliente local |
| Tauri desktop | experiencia principal Linux y control de procesos conocidos |
| Deskflow | compartir input entre estaciones |
| RustDesk client | control remoto de pantalla/input |

## Por qué esta arquitectura es adecuada

### Reutiliza herramientas maduras

Yo no escribí un protocolo de escritorio remoto desde cero. RustDesk ya resuelve captura, codec, cifrado y relay; Deskflow resuelve input compartido. Sarmiento aporta identidad, inventario, coordinación y UX.

### Reduce privilegios

El frontend no recibe una shell. La aplicación nativa expone comandos específicos y validados: iniciar RustDesk con un ID permitido o controlar unidades Deskflow conocidas.

### Permite clientes diferentes

La misma API sirve a PWA, desktop y agentes. Cada cliente usa el contrato que necesita sin duplicar reglas de negocio.

### Conserva trazabilidad

Enrolamiento, rotación, login, revocación y acciones relevantes dejan eventos auditables.

## Decisiones principales

### D-01 — RustDesk OSS como motor remoto

**Yo elegí:** RustDesk OSS con servidor propio.

**Porque:** permite controlar infraestructura, identidad de servidor y relay sin desarrollar streaming remoto.

**Descarté:** crear un protocolo propio, porque sería inseguro, costoso y difícil de optimizar.

### D-02 — Deskflow separado de RustDesk

**Yo elegí:** usar Deskflow para el caso de equipos cercanos y RustDesk para sesión remota.

**Porque:** compartir input entre pantallas físicas no necesita codificar video; abrir una máquina en un monitor sí.

**Diferencia:** Deskflow extiende el escritorio físico; RustDesk muestra/controla otra sesión.

### D-03 — Control-plane central

**Yo elegí:** FastAPI + PostgreSQL como autoridad de inventario y credenciales.

**Porque:** necesito estado durable, consultas, transacciones, locks y auditoría.

### D-04 — Agentes ligeros por sistema operativo

**Yo elegí:** agentes específicos para Linux, Windows y macOS.

**Porque:** instalación, almacenamiento de credenciales, servicios y permisos cambian por plataforma.

**Regla:** el agente no decide permisos del owner ni ejecuta comandos arbitrarios.

### D-05 — Enrolamiento de un solo uso

**Yo elegí:** tokens consumidos una sola vez con bloqueo transaccional.

**Porque:** evita que una carrera registre varios equipos con el mismo token.

### D-06 — Rotación tolerante a fallos

**Yo elegí:** mantener la credencial vieja hasta verificar que la nueva fue persistida y utilizada.

**Porque:** revocar primero puede dejar un equipo desconectado si se pierde la respuesta.

**Costo aceptado:** existe una ventana controlada con dos credenciales válidas, registrada y acotada.

### D-07 — Credenciales con HMAC/hash en servidor

**Yo elegí:** no almacenar secretos de agentes en texto plano.

**Porque:** una fuga de base no debe entregar directamente todas las credenciales reutilizables.

### D-08 — Aplicación nativa Tauri

**Yo elegí:** Tauri 2 para Linux.

**Porque:** necesito bandeja, autostart, deep links, procesos locales, systemd user y cliente HTTPS nativo.

**Descarté como experiencia principal:** una web pura, porque el navegador no puede controlar estos recursos locales de forma segura y directa.

### D-09 — PWA como complemento

**Yo elegí:** mantener el panel web.

**Porque:** sirve desde teléfono, para administración y como contingencia.

**Límite:** requiere companion/deep link para abrir recursos locales.

### D-10 — Sesión desktop en memoria

**Yo elegí:** no persistir cookies/tokens de la aplicación nativa en disco.

**Porque:** reduce el impacto de una copia del perfil o filesystem.

**Costo:** el usuario debe autenticarse después de reiniciar la app.

### D-11 — MFA TOTP y recovery codes

**Yo elegí:** segundo factor y códigos de recuperación de un solo uso.

**Porque:** el owner controla equipos; una contraseña sola no es suficiente.

### D-12 — Deep link limitado

**Yo elegí:** `sarmiento://` con acciones y campos validados.

**Porque:** un protocolo custom no debe convertirse en ejecución arbitraria desde una página.

### D-13 — Unidades systemd conocidas

**Yo elegí:** controlar solo nombres y operaciones Deskflow predefinidos.

**Porque:** exponer `systemctl` genérico equivaldría a una shell privilegiada.

### D-14 — Rollback de modo estación

**Yo elegí:** guardar/restaurar el estado de Deskflow al abrir RustDesk.

**Porque:** un fallo al lanzar el cliente remoto no debe dejar teclado y mouse sin su configuración anterior.

### D-15 — Migraciones fuera del serving

**Yo elegí:** Alembic como autoridad de esquema.

**Porque:** crear o modificar tablas desde cada proceso API genera carreras y permisos excesivos.

## Alternativas y diferencias

| Alternativa | Ventaja | Por qué no la elegí |
|---|---|---|
| AnyDesk/TeamViewer SaaS | configuración simple | dependencia externa, menor control y costos/licencias |
| RustDesk sin control-plane | menos código | sin inventario, políticas, rotación ni auditoría propias |
| solo Deskflow | consumo bajo en LAN | no muestra pantalla remota ni funciona igual fuera de la estación |
| solo RustDesk | un único programa | peor experiencia para compartir input entre pantallas físicas |
| Electron | ecosistema web amplio | mayor consumo y superficie para una app local de control |
| shell expuesta a frontend | flexibilidad | riesgo crítico de ejecución arbitraria |
| revocar credencial antes de rotar | implementación simple | puede cortar definitivamente el agente |

## Atributos de calidad priorizados

1. seguridad de acceso;
2. recuperabilidad;
3. disponibilidad de equipos;
4. auditabilidad;
5. experiencia de escritorio;
6. compatibilidad multiplataforma;
7. mantenibilidad;
8. escalabilidad.

## Deuda y límites reconocidos

- aceptación física por OS y compositor;
- Wayland más restrictivo que X11;
- firewall/NAT/relay dependientes de la red;
- operación de Deskflow específica de unidades configuradas;
- app nativa principal orientada a Linux/KDE;
- companion necesario para acciones locales desde PWA;
- observabilidad y alertas pueden ampliarse;
- retención de auditoría debe formalizarse por entorno.

## Regla de evolución

Yo no agrego una acción local a la app desktop hasta definir su allowlist, validación, auditoría, fallo seguro y rollback. La comodidad no justifica una shell general.