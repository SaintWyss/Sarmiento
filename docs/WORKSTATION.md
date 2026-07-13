# Estación de trabajo gráfica

Sarmiento puede coordinar Deskflow y RustDesk desde el panel PWA. La interfaz es el punto de
entrada; el navegador delega las acciones locales mediante el protocolo `sarmiento://`.

## Modos

### Pantallas físicas

Cada computadora conserva su propia pantalla. Deskflow comparte mouse, teclado y portapapeles.
El botón **Usar pantallas físicas** ejecuta:

```text
sarmiento://workstation/normal
```

El companion inicia `deskflow-server.service` en la sesión del usuario. Si no existe, intenta
`deskflow-client.service`.

### Abrir en monitor

Cada tarjeta online incluye **Abrir en monitor**. Después de confirmar, el panel ejecuta:

```text
sarmiento://workstation/notebook/<rustdesk-id>
```

El companion valida el ID, pausa Deskflow y abre RustDesk. La contraseña permanente nunca
atraviesa el panel ni el control-plane. Para volver al escritorio físico se usa el botón
**Usar pantallas físicas**.

## Instalación o actualización

Desde **Conexión 1-click**, ejecutá el instalador Linux que muestra el panel. Instala:

- `/opt/sarmiento-viewer/sarmiento-open.sh`: handler del protocolo.
- `/opt/sarmiento-viewer/sarmiento-workstation.sh`: coordinador local.
- `sarmiento-viewer.desktop`: asociación de `sarmiento://`.
- `sarmiento.desktop`: acceso al panel desde KDE.

El instalador no instala RustDesk ni configura Deskflow: verifica RustDesk y reutiliza los
servicios Deskflow existentes. Esto evita modificar la topología del usuario desde el panel.

## Seguridad

- Todos los IDs se validan con una allowlist estricta antes de llegar a un proceso.
- No se usa `eval` ni se construyen comandos mediante concatenación.
- El navegador no recibe acceso a systemd ni a un socket HTTP local.
- El companion se ejecuta como el usuario gráfico y solo controla servicios `systemd --user`.
- Sarmiento no lee ni persiste la contraseña permanente de RustDesk.

## Recuperación y rollback

Si RustDesk está abierto y querés recuperar el cruce de cursor, pulsá **Usar pantallas físicas**.
Si el protocolo local no responde, reinstalá el Viewer desde **Conexión 1-click**.

Para eliminar la integración:

```bash
sudo rm -rf /opt/sarmiento-viewer
sudo rm -f /usr/share/applications/sarmiento-viewer.desktop
sudo rm -f /usr/share/applications/sarmiento.desktop
update-desktop-database ~/.local/share/applications /usr/share/applications 2>/dev/null || true
```

Eliminar el Viewer no desinstala RustDesk, no modifica el agente y no borra la configuración
de Deskflow.

## Aceptación manual

1. Abrir Sarmiento desde KDE.
2. Pulsar **Abrir en monitor** sobre un equipo online.
3. Confirmar que Deskflow queda pausado y RustDesk abre el ID correcto.
4. Controlar el equipo en ventana y pantalla completa.
5. Pulsar **Usar pantallas físicas**.
6. Confirmar que Deskflow vuelve a estar activo y el cursor cruza entre pantallas.
7. Reiniciar la sesión y confirmar que el handler `sarmiento://` continúa registrado.
