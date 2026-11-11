# 4Fun launcher

A local landing page for Build4Fun, Code4Fun, and Crack4Fun. Start an app from a
local build or pull its released images from GHCR, open it, inspect Activity,
and stop it while keeping saved work.

## Start the launcher

Install Docker Engine and Compose. From the repository root:

```sh
cp .env.example .env  # Only if you do not already have a configured .env.
# On Docker Desktop for macOS, set B4F_DOCKER_SOCKET as described in .env.example.
docker compose -f compose.launcher.yaml up --build -d --wait
```

Open **http://localhost:8070**. Set `LAUNCHER_HTTP_PORT` to change its port.
The launcher detects the existing independent stacks; there is no need to
launch a second copy or migrate projects. The default app ports remain 8080,
8090, and 8100. Compose reads their port overrides from `.env`.

The repository is mounted read-only at its actual absolute host path, so Docker
build contexts and host workspace mounts resolve correctly. Keep this checkout
available while the launcher runs. The Docker socket is mounted separately.
This app has authority over the local Docker Engine and is intended for the
trusted instructor's machine. Its port binds only to localhost; learner
containers do not receive its socket or state volume.

## Choose how to launch

**Local build** uses the app's checked-in Compose file and Dockerfiles with
`up --build`. Changes to local sources are included. First builds can take
several minutes, especially Code4Fun's browser and Crack4Fun's tools/wordlist.

**GitHub Container Registry** pulls the specified tag (default `latest`), then
starts the app with `--no-build`. Every service uses a released image. The
launcher preserves the app's ports, volumes, networks, and resource settings.
Choose a tag compatible with the Compose definitions in your checkout.
It never falls back to building when a pull fails. Review Activity for a missing
tag, an unavailable package, or a failed health check.

Default registry repository: `ghcr.io/rayleeigh/educate4fun`. Set
`FOURFUN_REGISTRY` for a fork. Build4Fun retains its existing image path;
components use child paths:

| App | Image paths under the registry repository |
| --- | --- |
| Build4Fun | The repository itself |
| Code4Fun | `/code4fun-workspace`, `/code4fun-api` |
| Crack4Fun | `/crack4fun-workspace`, `/crack4fun-sandbox`, `/crack4fun-portal` |
| Launcher | `/launcher` |

The [release workflow guide](../../docs/releases.md) covers automatic and manual
publishing of all seven images. The workflow publishes on a `v…` release and updates
`latest` for stable releases. Newly added packages must be published before
GHCR mode can launch those apps. Configure package visibility as public for
anonymous pulls from the launcher container. Publishing workflow changes does
not itself publish images. New releases publish Linux AMD64 and ARM64 images. Before starting, choose
**ARM64** or **AMD64** on the app card. The small information button explains
the options: ARM64 for Apple Silicon and Raspberry Pi with a 64-bit OS; AMD64
for most Intel/AMD PCs and Intel Macs. This choice applies to both local builds
and registry images. Selecting a different architecture requires Docker
emulation; the launcher never changes the selection automatically. An older
AMD64-only tag cannot launch with ARM64 selected; use a newer native release,
a local ARM64 build, or explicitly select AMD64 on a host supporting emulation.


After the launcher image is published, its own bootstrap can also use GHCR:

```sh
# The usual bootstrap above builds locally; to pull instead:
docker pull ghcr.io/rayleeigh/educate4fun/launcher:latest
docker tag ghcr.io/rayleeigh/educate4fun/launcher:latest fourfun-launcher:local
docker compose -f compose.launcher.yaml up --no-build -d --wait
```

## Saved work and lifecycle

Start/update and Stop affect only the selected fixed Compose project. Stop does
not delete containers or volumes. Switching image source uses the same workspace
and progress volumes. Build4Fun's separately deployed apprentice environments
remain independent of its controller. Closing the Activity window or browser
does not cancel an operation. Closing the launcher does not stop learning apps.

Operations run one at a time per app, with a 45-minute limit and the last 100 KB
of output kept in memory. Activity logs clear when the launcher restarts. If it
restarts during a build/start, inspect Docker status before retrying. It does
not provide arbitrary Docker commands, delete volumes, or manage unrelated
projects. GHCR mode still uses this checkout's Compose definitions; this is a
repository-backed launcher, not a standalone registry catalog.

## Checks

```sh
python -m unittest discover -s apps/launcher/tests -v
python apps/launcher/tests/ui_smoke.py
# Optional real lifecycle checks, using an isolated project and workspace:
python apps/launcher/tests/docker_smoke.py --registry
```

The browser check requires Playwright/Chromium, as in the shared checks workflow.
It uses a fixture for lifecycle actions and does not stop existing learner apps.
