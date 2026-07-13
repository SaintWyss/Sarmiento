# Sarmiento

Sarmiento es una plataforma personal de control remoto para administrar tus propias computadoras desde cualquier lugar. Usa **RustDesk OSS** como motor de pantalla, teclado, mouse, audio, transferencia y relay, y agrega un **control-plane propio** para inventario, enrolamiento, presencia, seguridad, auditoría y conexión rápida.

## Estado

**Versión 1.0 implementada.** El repositorio contiene backend, panel web/PWA, agentes Linux, Windows y macOS, infraestructura Docker, HTTPS, base de datos, backups, pruebas y CI.

La validación automática cubre el control-plane y los agentes. La última aceptación siempre debe ejecutarse con las máquinas reales porque permisos de captura, Wayland, firewalls, NAT y permisos del protocolo local `sarmiento://` dependen del sistema operativo.

## Qué incluye

- RustDesk Server OSS self-hosted: `hbbs` + `hbbr`.
- Control-plane FastAPI + PostgreSQL.
- Inicio de sesión del propietario con cookie HttpOnly, CSRF y rate limiting.
- Tokens de enrolamiento de uso único y vencimiento configurable.
- Credenciales independientes por agente, almacenadas únicamente como hash.
- Heartbeat cada 30 segundos, estado online/offline e inventario técnico.
- Panel responsive instalable como PWA.
- Conexión 1-click mediante el protocolo local `sarmiento://` y copia del ID como fallback.
- Administración de alias, etiquetas, revocación y rotación de credenciales.
- Auditoría de accesos y cambios administrativos.
- Instaladores para Linux/systemd, Windows/Scheduled Tasks y macOS/launchd.
- Lanzador 1-click propio `sarmiento://` para Linux, Windows y macOS.
- HTTPS automático con Caddy.
- Migraciones Alembic, backups, restore, smoke tests y GitHub Actions.

## Arquitectura

```text
Browser / PWA
      │ HTTPS
      ▼
   Caddy ─────► FastAPI control-plane ─────► PostgreSQL
                    ▲       ▲
                    │       └── agente Linux / Windows / macOS (enroll + heartbeat)
                    │
                    └── inventario, auth y auditoría

RustDesk viewer ────── E2E / P2P o relay ────── RustDesk host
                  hbbs rendezvous + hbbr relay
```

El control-plane **no procesa video ni eventos de entrada** y **no guarda la contraseña permanente de RustDesk**. Esa contraseña se genera/configura en la máquina controlada y se muestra una sola vez durante la instalación.

## Requisitos de despliegue

- Servidor Linux con Docker Engine y Docker Compose.
- IP pública o VPS accesible desde las máquinas viewer y host.
- Un dominio para el panel, por ejemplo `control.example.com`.
- Un hostname o IP para RustDesk, por ejemplo `desk.example.com`.
- Puertos abiertos:
  - `80/tcp`, `443/tcp`, `443/udp` para el panel y HTTPS.
  - `21115/tcp`.
  - `21116/tcp` y `21116/udp`.
  - `21117/tcp`.
  - `21118/tcp` y `21119/tcp` si se conserva soporte web de RustDesk.

## Instalación del servidor

```bash
git clone https://github.com/SaintWyss/Sarmiento.git
cd Sarmiento

python3 ops/init_env.py \
  --site-address https://control.example.com \
  --rustdesk-server desk.example.com \
  --owner owner

make up
make smoke URL=https://control.example.com
```

El generador crea `infra/.env` con permisos `0600`, contraseña de PostgreSQL, secreto de sesión y pepper independientes. Si no ingresás una contraseña de propietario de forma interactiva, genera una y la muestra una sola vez.

Abrí el panel, iniciá sesión y pulsá **Añadir equipo**.

## Enrolar una máquina

El panel crea un token temporal y muestra el comando exacto.

Linux:

```bash
curl -fsSL https://control.example.com/agent/install-linux.sh | \
  sudo bash -s -- --url https://control.example.com --token 'set_...'
```

Windows PowerShell como administrador:

```powershell
iwr https://control.example.com/agent/install-windows.ps1 -UseBasicParsing | iex
Install-SarmientoAgent -Url 'https://control.example.com' -Token 'set_...'
```

macOS, con RustDesk ya instalado en `/Applications`:

```bash
curl -fsSL https://control.example.com/agent/install-macos.sh | sudo bash -s -- \
  --url https://control.example.com --token 'set_...'
```

Los instaladores:

1. Instalan RustDesk 1.4.9 en Linux/Windows cuando no está presente; en macOS verifican la aplicación instalada.
2. Configuran el ID Server y la clave pública del servidor.
3. Generan una contraseña permanente aleatoria de RustDesk.
4. Obtienen el ID mediante `rustdesk --get-id`.
5. Enrolan el equipo en Sarmiento.
6. Instalan el heartbeat persistente.
7. Muestran la contraseña permanente para guardarla en un gestor de contraseñas.

## Uso desde celular

1. Instalá el cliente oficial de RustDesk en el celular.
2. Configuralo con el mismo ID Server y clave pública que muestra Sarmiento.
3. Abrí Sarmiento en el navegador o instalalo como PWA.
4. Pulsá **Conectar**. Si el sistema no abre el deep link, copiá el ID y pegalo en RustDesk.

## Desarrollo y validación

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e 'control-plane[dev]'

make test
make check
```

Prueba local del backend:

```bash
cd control-plane
SARMIENTO_OWNER_PASSWORD='a-secure-local-password' \
SARMIENTO_SESSION_SECRET='replace-with-at-least-32-random-bytes' \
SARMIENTO_STATIC_DIR='../front' \
SARMIENTO_AGENT_DIR='../agent' \
SARMIENTO_VIEWER_DIR='../viewer' \
uvicorn sarmiento.main:app --reload
```

## Conexión 1-click

En cada equipo que usarás como visor, abrí **Conexión 1-click** en el panel y ejecutá una vez el instalador de protocolo. Desde entonces, **Conectar** abre RustDesk mediante `rustdesk --connect <ID>`. En Android/iOS se usa el cliente RustDesk configurado con el mismo servidor y clave; si el sistema no reconoce el protocolo, el panel muestra el ID para copiarlo.

## Operación

```bash
make logs
make ps
make backup
./ops/restore.sh backups/20260712T120000Z
```

Consultá:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md)
- [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md)

## Versiones fijadas

- RustDesk client: `1.4.9` en los instaladores.
- RustDesk server OSS: `1.1.15`.
- PostgreSQL: `16.4-alpine`.
- Python: `3.12`.

Las versiones se actualizan deliberadamente mediante PR, pruebas y aceptación en hardware. No se usa `latest` en producción.

## Licencias

El código propio de Sarmiento se publica bajo MIT. RustDesk se ejecuta como dependencia independiente y conserva su licencia AGPL-3.0-or-later. Ver [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
