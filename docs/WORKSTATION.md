# Sarmiento Desktop en KDE/X11

Sarmiento Desktop es una aplicación Linux nativa. Tiene ventana propia, aparece en el menú de
KDE, puede iniciar con la sesión y permanece disponible en la bandeja del sistema. El panel web
sigue existiendo para administración móvil o de emergencia, pero no es necesario para el uso
diario desde la PC.

## Qué controla

- **Pantallas físicas:** inicia el servicio Deskflow local para cruzar mouse, teclado y
  portapapeles entre la PC y la notebook.
- **Control remoto:** abre RustDesk contra el ID seleccionado y conserva Deskflow activo.
- **Abrir en monitor:** pausa Deskflow y abre RustDesk para usar la notebook dentro de uno de los
  monitores del escritorio.
- **Equipos y seguridad:** inicio de sesión, inventario, presencia, alias, etiquetas, revocación,
  rotación de agente, enrolamiento, contraseña y MFA desde la misma ventana.

Sarmiento no captura ni transporta video: RustDesk continúa haciendo esa tarea. Tampoco lee ni
guarda la contraseña permanente de RustDesk.

## Construcción

En CachyOS/Arch instalá una vez las herramientas de compilación:

```bash
sudo pacman -S --needed base-devel rust nodejs npm webkit2gtk-4.1 libappindicator-gtk3 librsvg
cd desktop
npm ci
npm run desktop:build
```

El AppImage queda en `desktop/src-tauri/target/release/bundle/appimage/`. La compilación de
`main` también lo publica en el Release `desktop-v1.0.0` para descargarlo sin compilar.

## Instalación local sin sudo

```bash
cd desktop
./install-linux.sh src-tauri/target/release/bundle/appimage/Sarmiento_*.AppImage
```

El instalador copia el programa a `~/.local/share/sarmiento-desktop/`, crea el acceso del menú KDE
y registra `sarmiento://`. Luego la operación completa se hace desde la interfaz.

Al abrir por primera vez:

1. Ingresá `https://sarmiento.lan`, el usuario owner y la contraseña vigente.
2. En **Ajustes**, activá **Iniciar Sarmiento con KDE** si lo querés permanente.
3. Usá **Abrir en monitor** en la notebook para el modo remoto.
4. Usá **Usar pantallas físicas** para volver a Deskflow.

Cerrar la ventana la oculta en la bandeja. **Salir** en el menú de la bandeja termina la
aplicación.

## Requisitos locales

- RustDesk accesible como `rustdesk`.
- Uno de `deskflow-server.service` o `deskflow-client.service` instalado como servicio
  `systemd --user`.
- CA interna del control-plane instalada en el trust store del sistema si se usa HTTPS privado.
- Sesión KDE/X11 con `DISPLAY` y `XAUTHORITY` importados en el user-manager, como en el despliegue
  existente.

## Seguridad

- La cookie de sesión y CSRF viven en memoria del proceso Rust, no en `localStorage`.
- Se exige HTTPS salvo en `localhost` para desarrollo.
- Los IDs RustDesk pasan por una allowlist antes de crear el proceso.
- No se usa un shell para ejecutar IDs ni se expone una API genérica de comandos al frontend.
- El CSP de la ventana no permite cargar scripts o contenido remoto.
- Deskflow se controla solo mediante `systemctl --user` y unidades conocidas.

## Desinstalación y recuperación

```bash
desktop/install-linux.sh --uninstall
```

Esto elimina únicamente Sarmiento Desktop. No toca RustDesk, Deskflow, el agente, el
control-plane ni sus credenciales. Si la app se cerrara mientras Deskflow está pausado, podés
recuperarlo con `systemctl --user start deskflow-server.service` (o `deskflow-client.service`).

## Aceptación física

1. Abrir Sarmiento desde el lanzador de KDE y autenticar.
2. Confirmar que muestra los dos equipos y el estado de Deskflow.
3. Pulsar **Abrir en monitor** sobre la notebook y verificar video, teclado y mouse en RustDesk.
4. Mover la ventana al monitor deseado y activar pantalla completa.
5. Pulsar **Usar pantallas físicas** y confirmar que el cursor vuelve a cruzar por Deskflow.
6. Activar autostart, reiniciar sesión y confirmar ventana/bandeja y handler `sarmiento://`.
