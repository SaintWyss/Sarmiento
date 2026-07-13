# Arquitectura de Sarmiento 1.0

## Principios

1. RustDesk conserva toda la responsabilidad de media, input, cifrado E2E, NAT traversal y relay.
2. Sarmiento mantiene una fuente de verdad propia para identidad, inventario y presencia.
3. El estado online se deriva del último heartbeat del agente; no se consulta el SQLite interno de `hbbs`.
4. Las contraseñas de RustDesk no ingresan al control-plane.
5. Los secretos de enrolamiento y agente se almacenan como HMAC-SHA-256 con pepper.

## Componentes

### Control-plane

Aplicación FastAPI desplegada detrás de Caddy. Sus capas son:

- `domain.py`: reglas puras de presencia y validez de enrolamiento.
- `services.py`: casos de uso y transacciones.
- `models.py`: modelos SQLAlchemy.
- `api.py`: transporte HTTP, cookies, CSRF y autenticación de agentes.
- `security.py`: scrypt, JWT, HMAC y generación criptográfica.

### Agentes

- Linux/macOS: agente Python sin dependencias externas.
- Windows: agente PowerShell nativo.
- El agente no ejecuta comandos remotos; únicamente configura RustDesk durante el enrolamiento y reporta telemetría acotada.
- El heartbeat se autentica con una credencial por dispositivo.

### Frontend

HTML, CSS y JavaScript sin framework ni cadena de build. La interfaz se sirve desde el mismo origen que la API, reduciendo CORS, distribución y superficie de supply chain. El service worker no cachea llamadas `/api/`.

### RustDesk

- `hbbs`: rendezvous, registro y hole punching.
- `hbbr`: relay.
- Los dos comparten un volumen persistente con la identidad del servidor.
- El control-plane monta el volumen en modo lectura para publicar `id_ed25519.pub` a los agentes.

## Flujos

### Login

1. El propietario envía usuario y contraseña.
2. La contraseña se verifica con scrypt.
3. Se entrega una cookie de sesión HttpOnly/SameSite=Strict y una cookie CSRF de doble envío.
4. Las mutaciones administrativas exigen `X-Sarmiento-CSRF`.

### Enrolamiento

1. El propietario crea un token de uso único.
2. El instalador obtiene la clave pública y configura RustDesk.
3. El agente envía inventario y el token.
4. El control-plane consume el token y devuelve una credencial de agente una sola vez.
5. Solo el hash de esa credencial se persiste.

### Presencia

1. El agente envía heartbeat cada 30 segundos.
2. Se actualiza `last_seen`.
3. Un equipo está online si no fue revocado y su heartbeat está dentro del umbral configurado.

### Conexión remota

1. El panel abre `sarmiento://connect/<id>`. El handler local valida el ID y ejecuta `rustdesk --connect <id>`; si no está instalado, el usuario puede copiar el ID.
2. El viewer RustDesk negocia con `hbbs`.
3. La sesión se establece P2P o mediante `hbbr`.
4. Sarmiento no participa en el canal de datos.

## Modelo de datos

- `owners`: propietario local.
- `devices`: identidad RustDesk, inventario, credencial hasheada y presencia.
- `enrollment_tokens`: tokens de un solo uso, TTL, consumo y revocación.
- `audit_events`: acciones de seguridad y administración.

## Decisiones deliberadas

- Single-owner en 1.0. No hay equipos, tenants ni RBAC porque el producto es personal.
- PostgreSQL en producción y SQLite para desarrollo/pruebas.
- Frontend estático para reducir mantenimiento.
- Caddy administra TLS.
- Sin almacenamiento central de contraseñas RustDesk.
