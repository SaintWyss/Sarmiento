# Arquitectura de Sarmiento 1.1

Sarmiento separa deliberadamente el **plano de control** del **plano de datos remoto**. El control-plane administra identidad, inventario, presencia y auditoría. RustDesk OSS transporta pantalla, entrada, audio y archivos mediante cifrado extremo a extremo, P2P o relay.

## Principios y límites

1. Sarmiento no reimplementa captura, codecs, NAT traversal ni input remoto.
2. PostgreSQL es la única fuente de verdad del control-plane.
3. `hbbs` no se consulta: la presencia se deriva del heartbeat autenticado del agente.
4. La contraseña permanente de RustDesk nunca entra al control-plane.
5. Tokens de enrolamiento y agente se persisten únicamente como HMAC-SHA-256 con pepper.
6. El propietario es único; no existe multi-tenancy ni RBAC en 1.1.
7. El canal de administración exige HTTPS, cookies seguras, CSRF y MFA opcional recomendado.

## Contexto del sistema

```mermaid
flowchart LR
    Owner[Propietario] -->|HTTPS + MFA| Panel[Sarmiento PWA]
    Panel --> Control[Control-plane]
    Agent[Agente en cada host] -->|Enroll + heartbeat HTTPS| Control
    Control --> DB[(PostgreSQL)]
    Viewer[Cliente RustDesk viewer] -->|Rendezvous| HBBS[hbbs]
    Host[Cliente RustDesk host] -->|Rendezvous| HBBS
    Viewer <-->|P2P cifrado E2E| Host
    Viewer <-->|Relay cifrado E2E si P2P falla| HBBR[hbbr]
    Host <-->|Relay cifrado E2E| HBBR
    Control -. no participa en media/input .- Viewer
```

## Contenedores y zonas de confianza

```mermaid
flowchart TB
    subgraph Internet[Zona no confiable: Internet]
      Browser[Navegador / PWA]
      RemoteAgent[Agentes remotos]
      RDClients[Clientes RustDesk]
    end

    subgraph Edge[Perímetro público]
      Caddy[Caddy :80/:443]
      HBBS[hbbs :21115/:21116/:21118]
      HBBR[hbbr :21117/:21119]
    end

    subgraph ControlNet[Red Docker privada: control]
      API[FastAPI :8000<br/>no publicado al host]
      DB[(PostgreSQL :5432<br/>no publicado al host)]
    end

    subgraph Volumes[Volúmenes persistentes]
      RDKeys[(rustdesk-data)]
      PGData[(postgres-data)]
      TLS[(caddy-data)]
    end

    Browser -->|TLS| Caddy --> API
    RemoteAgent -->|TLS| Caddy
    API --> DB
    RDClients --> HBBS
    RDClients --> HBBR
    HBBS --> RDKeys
    HBBR --> RDKeys
    DB --> PGData
    Caddy --> TLS
    API -. lectura de clave pública .-> RDKeys
```

La cabecera `X-Forwarded-For` se confía porque el API no publica puertos y solo Caddy comparte la red `control`. Publicar `api:8000` directamente invalidaría este supuesto de seguridad.

## Componentes del control-plane

```mermaid
flowchart LR
    API[api.py<br/>HTTP, cookies, CSRF] --> Services[services.py<br/>casos de uso y transacciones]
    Services --> Domain[domain.py<br/>reglas puras]
    Services --> Models[models.py<br/>SQLAlchemy]
    Services --> Security[security.py<br/>scrypt, JWT, TOTP, HMAC]
    API --> Schemas[schemas.py<br/>validación y límites]
    Main[main.py<br/>composición] --> API
    Main --> Middleware[middleware.py + rate_limit.py]
    Models --> DB[(PostgreSQL)]
```

## Modelo de dominio

```mermaid
classDiagram
    class Owner {
      +UUID id
      +string username
      +string password_hash
      +int session_version
      +int failed_login_count
      +datetime locked_until
      +string mfa_secret_encrypted
      +string[] mfa_recovery_hashes
    }
    class Device {
      +UUID id
      +string rustdesk_id
      +string alias
      +string token_hash
      +datetime last_seen
      +datetime revoked_at
      +string pending_token_hash
      +datetime credential_rotation_requested_at
    }
    class EnrollmentToken {
      +UUID id
      +string token_hash
      +datetime expires_at
      +datetime used_at
      +datetime revoked_at
    }
    class AuditEvent {
      +UUID id
      +string actor_type
      +string action
      +string target_id
      +json details
      +datetime created_at
    }
    Owner "1" --> "0..*" EnrollmentToken : creates
    Owner "1" --> "0..*" AuditEvent : produces
    Device "1" --> "0..*" AuditEvent : produces
```

## Modelo de persistencia

```mermaid
erDiagram
    OWNERS ||--o{ ENROLLMENT_TOKENS : creates
    OWNERS {
      uuid id PK
      varchar username UK
      text password_hash
      int session_version
      int failed_login_count
      timestamptz locked_until
      text mfa_secret_encrypted
      json mfa_recovery_hashes
      timestamptz mfa_enabled_at
    }
    DEVICES {
      uuid id PK
      varchar rustdesk_id UK
      varchar alias
      varchar token_hash UK
      varchar pending_token_hash UK
      timestamptz last_seen
      timestamptz revoked_at
      json metadata
    }
    ENROLLMENT_TOKENS {
      uuid id PK
      varchar token_hash UK
      uuid created_by FK
      timestamptz expires_at
      timestamptz used_at
      timestamptz revoked_at
    }
    AUDIT_EVENTS {
      uuid id PK
      varchar actor_type
      varchar actor_id
      varchar action
      varchar target_id
      varchar source_ip
      json details
      timestamptz created_at
    }
```

## Secuencia de login con MFA

```mermaid
sequenceDiagram
    actor U as Propietario
    participant P as PWA
    participant A as FastAPI
    participant D as PostgreSQL

    U->>P: usuario + contraseña + TOTP/recovery
    P->>A: POST /auth/login
    A->>D: cargar Owner
    A->>A: scrypt + lockout persistente
    alt MFA habilitado
      A->>A: descifrar secreto y verificar TOTP/recovery
      A->>D: guardar paso TOTP o consumir recovery
    end
    A->>D: reset fallos + last_login + audit
    A-->>P: cookie __Host-... HttpOnly + cookie CSRF
```

## Secuencia de enrolamiento

```mermaid
sequenceDiagram
    actor O as Propietario
    participant P as Panel
    participant C as Control-plane
    participant D as PostgreSQL
    participant I as Instalador
    participant R as RustDesk host

    O->>P: Crear token temporal
    P->>C: POST /enrollment-tokens + CSRF
    C->>D: guardar HMAC(token), TTL
    C-->>P: token una sola vez
    O->>I: ejecutar comando en el host
    I->>R: configurar server/key/password
    I->>C: POST /agents/enroll
    C->>D: SELECT token FOR UPDATE
    C->>D: consumir token + crear Device + HMAC(agent token)
    C-->>I: agent token una sola vez
```

## Rotación tolerante a fallos

```mermaid
sequenceDiagram
    actor O as Propietario
    participant C as Control-plane
    participant A as Agente
    participant D as PostgreSQL

    O->>C: solicitar rotación
    C->>D: guardar nonce y estado pendiente
    A->>C: heartbeat con token anterior
    C-->>A: credential_rotation_required=true
    A->>C: POST /agents/rotate-token
    C->>D: derivar token determinístico + guardar solo hash pendiente
    C-->>A: nuevo token
    A->>A: persistir token localmente
    A->>C: siguiente heartbeat con token nuevo
    C->>D: promover hash pendiente y revocar hash anterior
```

## Estado del dispositivo

```mermaid
stateDiagram-v2
    [*] --> NoEnrolado
    NoEnrolado --> ActivoOffline: token válido + enroll
    ActivoOffline --> ActivoOnline: heartbeat dentro del umbral
    ActivoOnline --> ActivoOffline: vence umbral
    ActivoOnline --> RotacionPendiente: propietario solicita rotación
    ActivoOffline --> RotacionPendiente: propietario solicita rotación
    RotacionPendiente --> ActivoOnline: nuevo token promovido + heartbeat
    RotacionPendiente --> ActivoOffline: nuevo token promovido sin heartbeat reciente
    ActivoOnline --> Revocado: revocar
    ActivoOffline --> Revocado: revocar
    RotacionPendiente --> Revocado: revocar
    Revocado --> ActivoOffline: nuevo enrolamiento explícito
```

## Decisiones no funcionales

- **Disponibilidad:** contenedores con healthchecks y `restart: unless-stopped`.
- **Consistencia:** migraciones Alembic; locks de fila para consumo y rotación.
- **Seguridad:** scrypt, MFA TOTP, recuperación de un uso, cookies `__Host-`, CSRF, CSP, HSTS, límites de cuerpo y metadata.
- **Observabilidad:** health/readiness, auditoría estructurada y logs JSON de Caddy.
- **Escala:** una instancia API prevista. Para múltiples workers se debe mover rate limiting a Redis, manteniendo PostgreSQL como autoridad.
