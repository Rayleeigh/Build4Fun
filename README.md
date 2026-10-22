# Build4Fun

Build4Fun introduces apprentices to Docker Compose through visual building
blocks. Create services, connect networks and storage, inspect the generated
YAML, and deploy the environment to a local Docker Engine.

Projects start with a project name and no prefilled services. Apprentices choose
the images, ports, paths, and settings themselves.

## Getting started

Install Docker with the Compose plugin and start the Docker Engine. From the
repository root:

```sh
cp .env.example .env
# Docker Desktop on macOS: set B4F_DOCKER_SOCKET in .env to
# ${HOME}/.docker/run/docker.sock
docker compose up --build -d --wait
```

Open http://localhost:8080. Compose stores projects in `.workspace/` by default
and publishes the application only on localhost. The application uses the host
Docker socket to deploy apprentice environments, so run it in a trusted local
learning environment.

To apply application or template changes, rerun the Compose command above.
Stop Build4Fun with `docker compose stop`; apprentice deployments remain running.

## Features

- Nested blocks with validation and a linked, live Compose preview.
- Independent projects, plain-text file editing, undo, and saved versions.
- Browser draft recovery after refresh.
- An interactive map of services, networks, host ports, and storage.
- Direct deployment with a change review, plus status, logs, stop, and removal.
- Compose downloads and project ZIP exports.

## Documentation

- [Setup and user guide](src/README.md): environment settings, editor workflow,
  deployment, troubleshooting, and checks.
- [Project purpose](docs/purpose.md): audience and learning approach.
- [Implementation](docs/implementation.md): architecture, persistence,
  validation, Docker execution, and current boundaries.
- [Environment example](.env.example): settings to copy into a local `.env`.

## Releases

Published GitHub releases with a `v` tag build and test the Docker image before
publishing to `ghcr.io/rayleeigh/build4fun:<release-tag>`. Stable releases also
update `latest`. See [release image validation](src/README.md#release-images).

## License

Read the [LICENSE](LICENSE) for the terms that apply to this project.
