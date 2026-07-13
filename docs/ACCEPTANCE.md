# Aceptación de Sarmiento 1.0

## Automatizada

- [x] Reglas de presencia y enrolamiento.
- [x] Hash y verificación de contraseña.
- [x] Emisión y validación de sesión.
- [x] Login correcto e incorrecto.
- [x] CSRF para mutaciones.
- [x] Token de enrolamiento de un solo uso.
- [x] Enrolamiento del dispositivo.
- [x] Heartbeat autenticado.
- [x] Inventario y estado online.
- [x] Edición, rotación y revocación.
- [x] Auditoría.
- [x] Migración inicial Alembic.
- [x] Sintaxis Python, Bash y JavaScript.

## Hardware real obligatoria

Ejecutar esta lista en cada plataforma antes de considerar aceptado un despliegue concreto:

- [ ] `hbbs` y `hbbr` accesibles desde una red externa.
- [ ] Clave pública visible en `/api/v1/config/public`.
- [ ] Instalación Linux completa.
- [ ] Instalación Windows completa.
- [ ] Instalación macOS completa y permisos TCC concedidos.
- [ ] Handler `sarmiento://` abre RustDesk desde el panel en cada sistema de escritorio.
- [ ] Equipo online en menos de 90 segundos.
- [ ] Conexión P2P desde otra red.
- [ ] Conexión forzada mediante relay.
- [ ] Teclado y mouse.
- [ ] Audio y portapapeles según política elegida.
- [ ] Transferencia de archivo.
- [ ] Reconexión después de reiniciar host.
- [ ] Revocación bloquea heartbeat.
- [ ] Restore de backup en un entorno aislado.
- [ ] Deep link desde escritorio.
- [ ] Conexión desde Android/iOS con el cliente RustDesk.
- [ ] Wayland o permisos macOS, cuando corresponda.

Los ítems de hardware no pueden validarse mediante unit tests porque dependen de red, permisos gráficos, firmware, NAT y aplicaciones instaladas.
