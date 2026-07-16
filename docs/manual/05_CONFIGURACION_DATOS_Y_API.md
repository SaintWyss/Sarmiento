# 05 — Configuración, datos y APIs

## Idea general

Yo separo la configuración por componente. El control-plane, RustDesk, agentes, PWA y aplicación desktop no deben compartir un `.env` ambiguo.

Cada despliegue debe identificar explícitamente:

- qué archivo de entorno usa;
- qué proceso lo consume;
- dónde viven los secretos;
- qué valores son locales, LAN o públicos;
- quién puede rotarlos.

## Control-plane

Las variables exactas se toman del código y `.env.example`, pero se agrupan en:

### Entorno y URLs

- modo de entorno;
- URL pública/base;
- hosts y orígenes permitidos;
- dominio/certificados;
- configuración de proxy confiable.

### Base de datos

- URL PostgreSQL;
- credenciales de runtime;
- credenciales separadas de migración cuando corresponda;
- pool y timeouts;
- directorio o volumen de backups.

### Autenticación

- secreto JWT;
- issuer y audience;
- duración de sesión;
- cookie names/flags;
- CSRF;
- bootstrap owner;
- cifrado/HMAC de MFA y credenciales;
- lockout y rate limits.

### Agentes

- frecuencia de heartbeat;
- expiración de presencia;
- tamaño de metadata;
- duración de tokens de enrolamiento;
- política de rotación.

### RustDesk

- host/puertos `hbbs` y `hbbr`;
- public key/identidad del servidor;
- volúmenes persistentes;
- versiones fijadas;
- relay y NAT.

## Regla sobre múltiples `.env`

Yo considero peligroso tener dos archivos de entorno con el mismo propósito y valores distintos. Antes de desplegar:

1. identifico qué Compose/servicio referencia cada archivo;
2. elimino copias obsoletas o las marco como ejemplos;
3. documento una única fuente activa;
4. respaldo la base/volúmenes antes de regenerar secretos;
5. no reemplazo credenciales de agentes sin un plan de migración.

## Datos persistidos

### PostgreSQL

Conceptos principales:

- owner y seguridad de acceso;
- MFA y recovery codes;
- dispositivos;
- tokens de enrolamiento;
- credenciales actuales y pendientes;
- rotaciones;
- heartbeats/presencia;
- alias y etiquetas;
- auditoría.

### Volúmenes RustDesk

Conservan:

- identidad/keys del servidor;
- configuración necesaria para que IDs y confianza no cambien inesperadamente.

Yo respaldo estos volúmenes junto con PostgreSQL. Recrearlos puede cambiar la identidad del servidor y obligar a reconfigurar clientes.

### Desktop y companion

Pueden conservar configuración no sensible como URL del servidor, preferencias de bandeja y unidades conocidas. La sesión se mantiene en memoria según el diseño actual.

### Agente

Cada agente guarda:

- device ID;
- credencial actual;
- URL del control-plane;
- estado mínimo para rotación;
- configuración de servicio.

Los permisos dependen del sistema operativo y deben restringirse al usuario/servicio.

## API del owner

Grupos conceptuales:

- autenticación y MFA;
- perfil/cambio de contraseña;
- inventario;
- tokens de enrolamiento;
- dispositivos, alias y etiquetas;
- revocación y rotación;
- auditoría;
- configuración/descarga de agentes o viewer cuando corresponda.

La lista exacta y schemas se toman del OpenAPI generado por el backend.

## API de agentes

Contratos principales:

- enrolamiento;
- heartbeat autenticado;
- obtención/aplicación de rotación;
- confirmación implícita mediante primer uso de la nueva credencial.

Yo separo estos endpoints de la sesión del owner. Un agente no recibe permisos administrativos.

## Autenticación del owner

El flujo usa:

- contraseña hasheada;
- lockout persistente;
- JWT/cookie con claims obligatorios;
- CSRF para operaciones mutables desde navegador;
- MFA TOTP;
- recovery codes almacenados mediante HMAC/hash;
- cookies `__Host-` cuando se usa HTTPS y las condiciones lo permiten.

## Autenticación del agente

El agente presenta una credencial larga y aleatoria. El servidor almacena una representación no reversible y compara de forma segura.

Durante una rotación puede existir:

- credencial actual;
- credencial pendiente;
- estado que permite promover la pendiente al primer uso.

## Protocolo `sarmiento://`

El payload debe representar una acción limitada, por ejemplo abrir un dispositivo por ID. Yo valido:

- esquema;
- acción;
- longitud y caracteres;
- ID RustDesk;
- origen/confirmación cuando corresponda;
- ausencia de argumentos extra.

No acepto comandos de shell, paths arbitrarios o URLs anidadas sin contrato.

## Deskflow

La app desktop conoce unidades/roles preconfigurados. El contrato local incluye acciones como:

- consultar estado;
- iniciar;
- detener/pausar;
- restaurar;
- verificar resultado.

No expone nombres de unidad suministrados libremente por el frontend.

## Errores

| Categoría | Ejemplo | Comportamiento |
|---|---|---|
| autenticación | contraseña/token inválido | 401 y lockout/rate limit según política |
| autorización | operación no permitida | 403 sin filtrar secretos |
| enrolamiento | token consumido/expirado | rechazo idempotente |
| rotación | estado inconsistente | conservar credencial válida y auditar |
| dispositivo | ID desconocido/revocado | no ejecutar acción |
| RustDesk | cliente o ID inválido | error accionable y rollback |
| Deskflow | unidad falla | restaurar estado previo |
| DB | migración/conexión | health degradado, no inventar esquema |
| metadata | payload excesivo | rechazo por límite |

## Versiones y compatibilidad

Yo fijo y documento versiones de:

- backend/runtime;
- PostgreSQL;
- Caddy;
- RustDesk server/client;
- Deskflow;
- agentes;
- desktop Tauri;
- schema/migración.

Una actualización de RustDesk o Deskflow requiere smoke real, no solo build.

## Regla de cambio

Cuando cambio una variable, claim, endpoint, tabla, payload de agente, deep link o unidad local, actualizo ejemplos, parser, validación, pruebas, UML, runbook y este capítulo.