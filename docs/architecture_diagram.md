# Sơ đồ kiến trúc

Tài liệu này được giữ làm đường dẫn tương thích. Sơ đồ và giải thích đầy đủ nằm tại [ARCHITECTURE.md](ARCHITECTURE.md).

```mermaid
flowchart LR
    Client[Swagger / HTTP client] -->|REST JSON| API[api/<br/>FastAPI adapters]
    Client <-->|WebSocket| API
    API --> APP[application/<br/>use cases]
    APP --> DOMAIN[domain/<br/>entities + protocols]
    INFRA[infrastructure/<br/>SQLAlchemy repositories] -. implements .-> DOMAIN
    INFRA --> DB[(SQLite / PostgreSQL)]
```
