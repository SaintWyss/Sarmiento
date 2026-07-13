# Despliegue

## Topología recomendada

Usar un VPS Linux con IP pública fija. Los registros DNS del panel y de RustDesk pueden apuntar a la misma IP:

```text
control.example.com A <IP-VPS>
desk.example.com    A <IP-VPS>
```

Caddy atiende el panel en 80/443. RustDesk usa 21115-21119.

## Firewall

Ejemplo con UFW:

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
sudo ufw allow 21115/tcp
sudo ufw allow 21116/tcp
sudo ufw allow 21116/udp
sudo ufw allow 21117/tcp
sudo ufw allow 21118/tcp
sudo ufw allow 21119/tcp
sudo ufw enable
```

## Generación de configuración

```bash
python3 ops/init_env.py \
  --site-address https://control.example.com \
  --rustdesk-server desk.example.com \
  --owner owner
```

No confirmes `infra/.env` en Git. Protegelo junto con los backups.

## Arranque

```bash
make up
make ps
make smoke URL=https://control.example.com
```

La clave pública de RustDesk se genera al iniciar `hbbs`. El API la lee dinámicamente desde el volumen compartido en modo read-only.

## DNS y certificados

Para HTTPS automático, `SARMIENTO_SITE_ADDRESS` debe ser una URL pública cuyo hostname resuelva al servidor. Para laboratorio local usá `http://localhost`, lo que desactiva la cookie Secure mediante el generador.

## Actualizaciones

1. Ejecutar backup.
2. Crear una rama y actualizar versiones fijadas.
3. Ejecutar pruebas y `docker compose build`.
4. Desplegar con `docker compose up -d --build`.
5. Ejecutar smoke y una conexión real.
6. Conservar el backup hasta completar la aceptación.

## Wayland y macOS

RustDesk puede requerir permisos interactivos de captura de pantalla, accesibilidad o portal PipeWire. Esos permisos pertenecen al sistema operativo y no deben intentar sortearse desde Sarmiento.

## Visores y protocolo local

El servidor entrega instaladores para registrar `sarmiento://` en Windows, Linux y macOS. El handler no acepta comandos arbitrarios: solo IDs con caracteres alfanuméricos, guion o guion bajo, y llama a RustDesk con `--connect`. Instalalo desde el botón **Conexión 1-click** del panel.
