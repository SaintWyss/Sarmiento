# UML y diagramas de comportamiento

Este documento concentra vistas UML complementarias a [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Casos de uso

```mermaid
flowchart LR
    Owner((Propietario))
    Agent((Agente))
    Viewer((Viewer RustDesk))

    Owner --> Login[Iniciar sesión con MFA]
    Owner --> Enroll[Crear token y enrolar host]
    Owner --> Inventory[Consultar inventario/presencia]
    Owner --> Manage[Editar, revocar o rotar agente]
    Owner --> Audit[Consultar auditoría]
    Owner --> Connect[Iniciar conexión 1-click]
    Agent --> Heartbeat[Reportar heartbeat e inventario]
    Agent --> Rotate[Rotar credencial automáticamente]
    Viewer --> Remote[Controlar host por RustDesk]
    Connect --> Remote
```

## Diagrama de componentes

```mermaid
classDiagram
    class APIRouter {
      +login()
      +enroll()
      +heartbeat()
      +manageDevice()
      +mfaLifecycle()
    }
    class AuthService {
      +verifyPassword()
      +verifySecondFactor()
      +registerFailure()
      +issueSession()
    }
    class EnrollmentService {
      +createToken()
      +consumeTokenForUpdate()
      +enrollDevice()
    }
    class DeviceService {
      +recordHeartbeat()
      +requestRotation()
      +promotePendingToken()
      +revoke()
    }
    class AuditService {
      +appendEvent()
      +listEvents()
    }
    class Repository {
      +SQLAlchemy Session
    }
    APIRouter --> AuthService
    APIRouter --> EnrollmentService
    APIRouter --> DeviceService
    AuthService --> AuditService
    EnrollmentService --> AuditService
    DeviceService --> AuditService
    AuthService --> Repository
    EnrollmentService --> Repository
    DeviceService --> Repository
    AuditService --> Repository
```

## Despliegue UML

```mermaid
flowchart TB
    subgraph VPS[Servidor Linux / VPS]
      subgraph Docker[Docker Compose]
        Caddy[Caddy]
        API[FastAPI non-root]
        PG[(PostgreSQL)]
        HBBS[hbbs]
        HBBR[hbbr]
      end
    end
    subgraph Workstation[PC controlada]
      HostRD[RustDesk host]
      Agent[Sarmiento Agent<br/>systemd/task/launchd]
    end
    subgraph Controller[PC o celular controlador]
      PWA[Sarmiento PWA]
      Viewer[RustDesk viewer]
      Handler[sarmiento:// handler<br/>desktop]
    end
    PWA -->|HTTPS 443| Caddy --> API --> PG
    Agent -->|HTTPS 443| Caddy
    HostRD -->|21115-21119| HBBS
    Viewer -->|21115-21119| HBBS
    Viewer --> HBBR
    HostRD --> HBBR
    PWA --> Handler --> Viewer
```

## Actividad de recuperación de acceso

```mermaid
flowchart TD
    Start[Login] --> Password{Contraseña válida?}
    Password -- No --> Fail[Incrementar fallo y auditar]
    Fail --> Locked{Umbral alcanzado?}
    Locked -- Sí --> Lock[Lockout temporal persistente]
    Locked -- No --> EndFail[401]
    Password -- Sí --> IsLocked{Cuenta bloqueada?}
    IsLocked -- Sí --> End429[429 + Retry-After]
    IsLocked -- No --> MFA{MFA habilitado?}
    MFA -- No --> Success[Crear sesión]
    MFA -- Sí --> Verify{TOTP nuevo o recovery válido?}
    Verify -- No --> Fail
    Verify -- TOTP --> SaveStep[Guardar step anti-replay]
    Verify -- Recovery --> Consume[Consumir código]
    SaveStep --> Success
    Consume --> Success
```
