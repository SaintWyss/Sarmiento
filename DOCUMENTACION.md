# Documentación de Sarmiento

Yo organicé la documentación de Sarmiento para que una persona sin conocimientos de redes, RustDesk, Deskflow, FastAPI o Tauri pueda entender cómo se conectan las piezas y qué necesita configurar en cada equipo.

## Recorrido recomendado

1. [Producto y primeros pasos](docs/manual/01_PRODUCTO_Y_PRIMEROS_PASOS.md)
2. [Uso funcional](docs/manual/02_USO_FUNCIONAL.md)
3. [Arquitectura y decisiones](docs/manual/03_ARQUITECTURA_Y_DECISIONES.md)
4. [Diagramas UML](docs/manual/04_UML.md)
5. [Configuración, datos y APIs](docs/manual/05_CONFIGURACION_DATOS_Y_API.md)
6. [Seguridad, pruebas y calidad](docs/manual/06_SEGURIDAD_PRUEBAS_Y_CALIDAD.md)
7. [Operación, despliegue y recuperación](docs/manual/07_OPERACION_DESPLIEGUE_Y_RECUPERACION.md)
8. [Estado, limitaciones, roadmap y glosario](docs/manual/08_ESTADO_LIMITACIONES_Y_GLOSARIO.md)

## Criterio editorial

- Escribí todo en español y en primera persona.
- Explico primero el objetivo cotidiano y después protocolos, servicios y seguridad.
- Diferencio control remoto, compartición de teclado/ratón y administración de dispositivos.
- Separo la aplicación de escritorio, la PWA y el servidor.
- No presento aceptación física o Wayland como validada si requiere hardware real.

## Fuente de verdad

1. código, migraciones, agentes y pruebas;
2. este manual normalizado;
3. documentación avanzada de `docs/`;
4. release notes y planes históricos.

Credenciales de agentes, owner, MFA, RustDesk y archivos `.env` reales nunca se incluyen en el repositorio ni en ejemplos completos.