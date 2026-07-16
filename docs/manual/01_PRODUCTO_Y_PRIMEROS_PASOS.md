# 01 — Producto y primeros pasos

## Explicación simple

Yo construí Sarmiento para administrar y controlar mis computadoras desde una interfaz propia.

Sarmiento reúne tres problemas distintos:

1. **inventario y seguridad:** saber qué equipos existen, si están conectados y quién puede usarlos;
2. **control remoto:** abrir una sesión de RustDesk hacia una máquina;
3. **estación compartida:** usar Deskflow para compartir teclado y mouse entre equipos cercanos.

La aplicación nativa es la experiencia principal de escritorio. El panel web/PWA continúa como complemento móvil y de emergencia.

## Ejemplo cotidiano

Pienso Sarmiento como una central de control:

- el control-plane es la recepción que conoce cada equipo;
- los agentes son los dispositivos que informan su estado;
- RustDesk es la cámara y control remoto;
- Deskflow es el cable invisible que comparte teclado y mouse;
- la app de escritorio es el tablero principal;
- la PWA es el control de bolsillo.

## Cómo lo explicaría yo

> Yo uso Sarmiento para registrar mis PCs, ver si están disponibles y elegir entre trabajar con sus pantallas físicas mediante Deskflow o abrir una sesión remota con RustDesk.

## Componentes principales

- control-plane FastAPI;
- PostgreSQL y Alembic;
- Caddy/TLS;
- servidor RustDesk OSS (`hbbs`/`hbbr`);
- agentes Linux, Windows y macOS;
- PWA web;
- companion/protocolo `sarmiento://`;
- aplicación Tauri 2 para Linux;
- integración con unidades `systemd --user` de Deskflow;
- auditoría, enrolamiento, rotación y MFA.

## Requisitos básicos

### Servidor/control-plane

- Linux con Docker y Docker Compose;
- dominio o acceso LAN según topología;
- puertos definidos;
- PostgreSQL persistente;
- almacenamiento para identidad RustDesk y backups.

### Equipos administrados

- agente correspondiente al sistema operativo;
- RustDesk instalado;
- Deskflow cuando se comparte teclado/mouse;
- permisos de pantalla, input y accesibilidad;
- conectividad hacia control-plane y servidor RustDesk.

### Aplicación nativa

- Linux KDE/X11 como entorno principal validado;
- AppImage o instalación local;
- servicios `systemd --user` esperados;
- cliente RustDesk disponible.

## Inicio del servidor

El procedimiento exacto depende del layout vigente, pero el flujo es:

```bash
cp .env.example .env
# Generar secretos, no copiar valores de ejemplo a producción.
docker compose up -d --build
docker compose ps
```

Después verifico health y HTTPS según el runbook.

## Crear owner

Yo creo el owner mediante el flujo de bootstrap documentado y luego elimino o desactivo la contraseña bootstrap. Activo MFA y guardo códigos de recuperación fuera del servidor.

## Enrolar primer equipo

1. generar token de enrolamiento de un solo uso;
2. instalar el agente en la máquina;
3. pasar URL y token por un canal seguro;
4. ejecutar enrolamiento;
5. verificar aparición en inventario;
6. asignar alias y etiquetas;
7. comprobar heartbeat;
8. probar rotación de credencial sin perder acceso.

## Instalar aplicación de escritorio

Uso el instalador o AppImage publicado para la versión. La instalación de usuario debe:

- copiar archivos sin `sudo` cuando sea posible;
- registrar desktop entry;
- registrar `sarmiento://`;
- configurar bandeja/autostart según elección;
- no persistir sesión en disco.

## Primera prueba segura

1. iniciar sesión en la app;
2. completar MFA;
3. ver inventario;
4. seleccionar una máquina;
5. probar solo lectura/estado;
6. activar “Pantallas físicas” y comprobar Deskflow;
7. volver al estado anterior;
8. probar “Abrir en monitor” con RustDesk;
9. verificar rollback de Deskflow;
10. revisar auditoría.

## Qué no debo asumir

- El panel web no reemplaza una app nativa aunque comparta funciones.
- RustDesk y Deskflow resuelven problemas distintos.
- Una máquina “online” no garantiza permisos de pantalla/input.
- Wayland puede requerir permisos y comportamiento diferentes.
- NAT, firewall y relay deben probarse en la red real.
- El sistema no puede validar físicamente monitores desde CI.

## Criterio para avanzar

Yo considero el entorno listo cuando:

- owner y MFA funcionan;
- agentes rotan credenciales;
- RustDesk usa el servidor esperado;
- Deskflow puede pausarse y reanudarse;
- la app abre el equipo correcto;
- existe rollback;
- backups y restore fueron probados;
- los permisos del OS fueron aceptados en hardware real.