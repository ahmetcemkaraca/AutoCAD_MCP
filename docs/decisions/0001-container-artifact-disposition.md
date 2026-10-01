# Context

The repository contains root `Dockerfile` and `docker-compose.yml` artifacts. They describe a Linux HTTP deployment, while the supported product target is full AutoCAD 2021-2026 on Windows. This record classifies those artifacts before any removal.

# Product runtime boundary

The supported product runtime requires the Windows COM boundary used by full AutoCAD 2021-2026 on Windows. A Linux container cannot provide that boundary, so the current Linux image cannot represent a supported product runtime. Linux remains suitable only for AutoCAD-independent tests; it is not evidence of AutoCAD compatibility.

# Reproducible observations

The following static checks were run from the repository root on the current host:

```text
requirements.txt=false
requirements-prod.txt=false
init.sql=false
nginx.conf=false
ssl=false
docker: command not found
```

The checks used a filesystem existence loop and `command -v docker`. Because the Docker CLI is unavailable, neither `docker compose -f docker-compose.yml config` nor an image build was run. This record makes no claim that either unrun operation failed.

`Dockerfile` declares `FROM python:3.12-slim`, `LABEL version="1.0.0"`, and `COPY requirements.txt requirements-prod.txt ./`; it probes `http://localhost:8000/health` and starts `src.mcp_integration.enhanced_mcp_server`. `docker-compose.yml` configures Redis, PostgreSQL, and nginx; it mounts the missing `init.sql`, `nginx.conf`, and `ssl` inputs and also probes `/health`.

# Options considered

1. Retain the artifacts as a supported product deployment. This requires a feasible Windows COM path and tests proving the supported AutoCAD runtime.
2. Retain the artifacts under a clearly experimental archive. This requires a named current consumer.
3. Remove the two root artifacts because they are incomplete, select the wrong server, and cannot host the supported runtime.

# Decision

Recommend option 3: remove `Dockerfile` and `docker-compose.yml`. The static evidence shows missing required inputs, an incompatible Linux product boundary, and a server and HTTP health contract that do not establish the adopted supported runtime.

Deletion requires explicit maintainer approval at E01-G3, including agreement that Git history is sufficient recovery. That approval has not occurred, and no deletion has occurred. This agent review does not substitute for maintainer authority.

# Consequences

Until E01-G3 explicitly approves removal, the root artifacts remain present but are not a supported product deployment. The Docker CLI absence prevents compose-config and image-build evidence on this host; it does not turn either unrun operation into a failure result. After approval, removal must be a focused change that checks active documentation for stale Docker runtime instructions.

# Reintroduction criteria

Reintroduction requires a named current consumer, a documented purpose that does not misrepresent the Windows COM product boundary, and a feasible supported runtime path. It must include complete, versioned build and compose inputs; a selected supported server contract; and reproducible config, build, and relevant runtime tests on the declared platforms. Any container presented as a product deployment must prove how full AutoCAD 2021-2026 on Windows and its COM boundary are supported.
