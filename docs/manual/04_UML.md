# 04 — Diagramas UML

## Propósito

Yo uso UML para separar actores, estructura, mensajes, estados y despliegue. Sarmiento combina web, desktop, agentes y servicios externos; sin varias vistas, es fácil confundir quién autentica, quién controla y quién transporta la sesión remota.

## Cobertura UML 2

| Tipo | Cobertura | Aplicación |
|---|---|---|
| casos de uso | incluida | owner, agentes y equipos |
| clases | incluida | identidad, dispositivo y rotación |
| objetos | incluida | equipo enrolado concreto |
| componentes | incluida | control-plane, clientes y servicios |
| paquetes | incluida | backend y adaptadores |
| estructura compuesta | incluida | interior de la app desktop |
| despliegue | incluida | servidor, PCs y red |
| actividad | incluida | enrolamiento y modo estación |
| estados | incluida | dispositivo y rotación |
| secuencia | incluida | login, enrolamiento y conexión |
| comunicación | incluida | mensajes principales |
| visión general de interacción | incluida | recorrido completo |
| temporal | incluida | heartbeat y rotación |
| perfil | incluida | estereotipos de seguridad |

## 1. Casos de uso

```mermaid
flowchart LR
    O[Owner]
    A[Agente]
    PC[Equipo administrado]
    WEB[Navegador/teléfono]

    O --> U1((Iniciar sesión con MFA))
    O --> U2((Ver inventario))
    O --> U3((Crear token de enrolamiento))
    O --> U4((Rotar o revocar equipo))
    O --> U5((Abrir sesión RustDesk))
    O --> U6((Activar modo Deskflow))
    O --> U7((Revisar auditoría))
    A --> U8((Enrolarse))
    A --> U9((Enviar heartbeat))
    A --> U10((Aplicar rotación))
    WEB --> U2
    PC --> U5
    PC --> U6
```

## 2. Clases de dominio

```mermaid
classDiagram
    class Owner {
      +id
      +email
      +passwordHash
      +mfaEnabled
      +lockedUntil
    }
    class Device {
      +id
      +alias
      +os
      +rustdeskId
      +status
      +lastSeenAt
      +revokedAt
    }
    class EnrollmentToken {
      +tokenHash
      +expiresAt
      +consumedAt
    }
    class DeviceCredential {
      +credentialHash
      +state
      +createdAt
      +promotedAt
    }
    class Rotation {
      +status
      +requestedAt
      +completedAt
    }
    class AuditEvent {
      +actor
      +action
      +target
      +result
      +createdAt
    }
    class WorkstationMode {
      +deskflowState
      +rustdeskSession
    }

    Owner "1" --> "*" Device
    EnrollmentToken --> Device : crea
    Device "1" --> "*" DeviceCredential
    Device "1" --> "0..1" Rotation
    Owner "1" --> "*" AuditEvent
    Device "1" --> "*" AuditEvent
    Device --> WorkstationMode
```

## 3. Objetos de un equipo

```mermaid
flowchart LR
    O[owner: Owner<br/>mfa=true]
    D[device: Device<br/>alias=Notebook<br/>status=online]
    C1[credentialOld<br/>state=current]
    C2[credentialNew<br/>state=pending]
    R[rotation<br/>status=awaiting-first-use]

    O --> D
    D --> C1
    D --> C2
    D --> R
```

## 4. Componentes

```mermaid
flowchart TB
    PWA[PWA]
    DESK[Tauri Desktop]
    COMP[Companion / sarmiento://]
    API[FastAPI Control Plane]
    AUTH[Auth + MFA + CSRF]
    DEV[Device/Enrollment Service]
    AUD[Audit Service]
    PG[(PostgreSQL)]
    AG[Agents Linux/Windows/macOS]
    HBBS[RustDesk hbbs]
    HBBR[RustDesk hbbr]
    RD[RustDesk Client]
    DF[Deskflow Services]

    PWA --> API
    PWA --> COMP
    DESK --> API
    DESK --> RD
    DESK --> DF
    COMP --> RD
    AG --> API
    API --> AUTH
    API --> DEV
    API --> AUD
    AUTH --> PG
    DEV --> PG
    AUD --> PG
    RD --> HBBS
    RD --> HBBR
```

## 5. Paquetes backend

```mermaid
flowchart LR
    HTTP[interfaces/http]
    APP[application]
    DOMAIN[domain]
    INFRA[infrastructure]
    DB[database/migrations]
    SECURITY[security]

    HTTP --> APP
    APP --> DOMAIN
    INFRA --> APP
    INFRA --> DOMAIN
    INFRA --> DB
    HTTP --> SECURITY
    SECURITY --> APP
```

## 6. Estructura compuesta de la app desktop

```mermaid
flowchart TB
    subgraph DesktopApp
      UI[WebView UI]
      CMD[Tauri Commands]
      HTTP[HTTPS Client]
      SESSION[In-memory Session]
      DEEP[Deep-link Handler]
      TRAY[Tray/Autostart]
      DESKFLOW[Deskflow Controller]
      RUSTDESK[RustDesk Launcher]
      ROLLBACK[State/Rollback]
    end

    UI --> CMD
    CMD --> HTTP
    HTTP --> SESSION
    CMD --> DEEP
    CMD --> TRAY
    CMD --> DESKFLOW
    CMD --> RUSTDESK
    DESKFLOW --> ROLLBACK
    RUSTDESK --> ROLLBACK
```

## 7. Actividad de enrolamiento

```mermaid
flowchart TD
    A[Owner crea token] --> B[Servidor guarda hash + expiración]
    B --> C[Agente envía token y metadata]
    C --> D{¿token válido y no consumido?}
    D -- no --> E[Rechazar y auditar]
    D -- sí --> F[Bloquear fila/consumir]
    F --> G[Crear Device]
    G --> H[Emitir credencial]
    H --> I[Agente persiste secreto]
    I --> J[Primer heartbeat]
    J --> K[Inventario online]
```

## 8. Actividad de “Abrir en monitor”

```mermaid
flowchart TD
    A[Seleccionar equipo] --> B[Validar RustDesk ID]
    B --> C[Leer estado Deskflow]
    C --> D[Pausar unidades conocidas]
    D --> E[Lanzar RustDesk]
    E --> F{¿lanzamiento correcto?}
    F -- no --> G[Restaurar Deskflow]
    F -- sí --> H[Sesión remota]
    H --> I[Cerrar/terminar]
    I --> G
    G --> J[Auditar resultado]
```

## 9. Máquina de estados del dispositivo

```mermaid
stateDiagram-v2
    [*] --> Unenrolled
    Unenrolled --> Enrolling: token válido
    Enrolling --> Active: credencial persistida + heartbeat
    Active --> Offline: heartbeat vencido
    Offline --> Active: heartbeat válido
    Active --> RotationPending: owner solicita rotación
    RotationPending --> NewCredentialIssued: agente solicita
    NewCredentialIssued --> Active: primer heartbeat con nueva credencial
    Active --> Revoked: owner revoca
    Offline --> Revoked: owner revoca
    Revoked --> [*]
```

## 10. Secuencia de login

```mermaid
sequenceDiagram
    actor O as Owner
    participant C as Desktop/PWA
    participant A as API
    participant DB as PostgreSQL

    O->>C: email + contraseña
    C->>A: login
    A->>DB: validar hash + lockout
    DB-->>A: owner válido
    A-->>C: desafío MFA
    O->>C: TOTP/recovery code
    C->>A: completar MFA
    A->>DB: validar/consumir
    A-->>C: sesión segura
```

## 11. Secuencia de rotación tolerante a fallos

```mermaid
sequenceDiagram
    actor O as Owner
    participant A as API
    participant D as Agent
    participant DB as PostgreSQL

    O->>A: solicitar rotación
    A->>DB: crear estado pending
    D->>A: heartbeat con credencial actual
    A-->>D: rotation_required
    D->>A: solicitar nueva credencial
    A->>DB: crear pending credential
    A-->>D: nueva credencial
    D->>D: persistir de forma segura
    D->>A: heartbeat con nueva credencial
    A->>DB: promover nueva y revocar anterior
    A-->>D: rotación completada
```

## 12. Comunicación

```mermaid
flowchart LR
    AG[Agent] -- enroll/heartbeat --> API[Control Plane]
    API -- rotation instruction --> AG
    DESK[Desktop] -- inventory/action --> API
    DESK -- validated ID --> RD[RustDesk]
    DESK -- service command --> DF[Deskflow]
    PWA -- deep link --> COMP[Companion]
    COMP -- validated launch --> RD
```

## 13. Visión general de interacción

```mermaid
flowchart TD
    I1[[Autenticar owner]] --> I2[[Consultar inventario]]
    I2 --> D{Objetivo}
    D -- nuevo equipo --> I3[[Crear token y enrolar]]
    D -- pantalla física --> I4[[Activar Deskflow]]
    D -- monitor remoto --> I5[[Pausar Deskflow + abrir RustDesk]]
    D -- seguridad --> I6[[Rotar/revocar]]
    I3 --> I2
    I4 --> I2
    I5 --> I7[[Restaurar Deskflow]]
    I7 --> I2
    I6 --> I2
```

## 14. Temporal: heartbeat y presencia

```mermaid
sequenceDiagram
    participant D as Device
    participant A as API
    participant I as Inventory

    D->>A: t0 heartbeat
    A->>I: online, last_seen=t0
    Note over I: ventana de presencia
    D->>A: t1 heartbeat
    A->>I: refrescar last_seen
    Note over D,A: si no llega heartbeat antes del umbral
    I->>I: marcar offline
    D->>A: t2 heartbeat válido
    A->>I: volver a online
```

## 15. Despliegue

```mermaid
flowchart TB
    subgraph Server[Servidor/VPS o LAN]
      CADDY[Caddy TLS]
      API[FastAPI]
      PG[(PostgreSQL)]
      HBBS[hbbs]
      HBBR[hbbr]
      VOL[Volumes/backups]
    end

    subgraph PC1[PC principal]
      DESK[Sarmiento Desktop]
      RD1[RustDesk Client]
      DFS[Deskflow Server]
      AG1[Agent]
    end

    subgraph PC2[Notebook]
      RD2[RustDesk Client]
      DFC[Deskflow Client]
      AG2[Agent]
    end

    PHONE[Teléfono/PWA] --> CADDY
    DESK --> CADDY
    AG1 --> CADDY
    AG2 --> CADDY
    CADDY --> API
    API --> PG
    RD1 --> HBBS
    RD2 --> HBBS
    RD1 --> HBBR
    RD2 --> HBBR
    DFS <--> DFC
    Server --> VOL
```

## 16. Perfil UML de seguridad

```mermaid
classDiagram
    class EnrollmentToken {
      <<one-time>>
      <<stored-as-hash>>
    }
    class DeviceCredential {
      <<secret>>
      <<rotation-tolerant>>
    }
    class DesktopCommand {
      <<allowlisted>>
      <<no-general-shell>>
    }
    class OwnerSession {
      <<mfa-protected>>
      <<in-memory-on-desktop>>
    }
    class AuditEvent {
      <<durable-evidence>>
    }
    class RustDeskId {
      <<validated-input>>
    }
```

## Regla de mantenimiento

Yo actualizo estas vistas cuando cambia un actor, estado de dispositivo, protocolo de rotación, acción desktop, servicio o nodo de despliegue. Los diagramas técnicos existentes complementan estas vistas para implementación detallada.