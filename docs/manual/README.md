# Manual normalizado de Sarmiento

Yo diseñé este manual con la misma receta que uso en mis otros sistemas. El lector empieza por el caso de uso y termina pudiendo desplegar, operar, respaldar y diagnosticar la plataforma.

## Capítulos

| Capítulo | Resultado esperado |
|---|---|
| 01 | comprender Sarmiento y levantar un entorno básico |
| 02 | usar inventario, enrolamiento, acceso remoto y modos de estación |
| 03 | entender arquitectura y decisiones |
| 04 | recorrer vistas UML |
| 05 | configurar servicios, agentes, datos y APIs |
| 06 | conocer seguridad, pruebas y calidad |
| 07 | desplegar, respaldar, restaurar y responder a incidentes |
| 08 | distinguir estado, límites, roadmap y vocabulario |

## Estados

- **Implementado:** existe un flujo conectado.
- **Probado:** existe evidencia automática.
- **Aceptado en hardware:** se comprobó en máquinas reales.
- **Parcial:** falta integración o cobertura.
- **Externo:** depende de red, permisos, sistema operativo o infraestructura.

## Documentación avanzada

Yo conservo los documentos existentes de arquitectura, UML, seguridad, despliegue, operaciones, workstation, aceptación y aplicación desktop. Este manual es la ruta para principiantes y la fuente común de formato.

## Regla de mantenimiento

Cuando cambia un endpoint, agente, protocolo, unidad systemd, versión RustDesk/Deskflow, flujo de rotación o app desktop, yo actualizo este manual y la evidencia operativa en el mismo pull request.