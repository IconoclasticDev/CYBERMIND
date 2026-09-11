# CYBERMIND sandbox

This sandbox is intentionally **non-destructive** and network-isolated. It exists to exercise the integration/demo path. It does not contain an exploit engine and does not make outbound network connections.

Start:

```bash
docker compose -f sandbox/docker-compose.yml up -d
```

Stop:

```bash
docker compose -f sandbox/docker-compose.yml down
```
