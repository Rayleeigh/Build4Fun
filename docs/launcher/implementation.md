# Launcher implementation

The landing page in `apps/launcher/` is a Python standard-library HTTP app with
plain HTML/CSS/JavaScript. Its container includes Docker CLI and Compose, using
the same image layout as Build4Fun. `compose.launcher.yaml` exposes loopback
port 8070, mounts the checkout read-only at its actual host path, mounts the
configured Docker socket, and gives the launcher a private named state volume.
It has no role in learner request routing. The three apps remain independent.

## Lifecycle

`catalog.py` fixes the allowed app IDs and maps every service to a registry
component. API callers cannot choose Compose paths, command-line arguments, or
shell commands. `manager.py` runs argument arrays without a shell and sets the
project directory and project name explicitly. Its environment resolves `.env`
using the host repository path rather than a container-specific working path.

Local mode invokes the original Compose file with `up --build -d --wait`.
Registry mode renders `compose config --format json`, removes each service's
`build`, substitutes a GHCR image using a validated tag, and writes a generated
configuration in the state volume. It pulls before calling `up --no-build`.
Build4Fun keeps `ghcr.io/<owner>/<repository>:<tag>`; other components live under
`ghcr.io/<owner>/<repository>/<component>:<tag>`. Switching source retains the
same project and mounts. Stopping invokes `compose stop`, preserving volumes.

Each app permits one background operation at a time. Different apps can start
independently. Commands have a 45-minute timeout; the last 100 KB of output is
polled by the UI through `/api/state`. Logs and jobs are held in memory and clear
on launcher restart. A periodic inspector reads Compose container state and
health independently of browser requests. It identifies incomplete and unhealthy
stacks and reads published app ports from the resolved Compose configuration.

## Local trust boundary

Managing Docker is privileged. The launcher is intended for a trusted local
instructor, never public hosting. Loopback publishing and exact Host/Origin
checks protect its lifecycle API from remote pages. A restrictive content policy
and text-only log rendering prevent activity output from becoming executable
markup. It offers no arbitrary Docker API, deletion, or general command endpoint.
The mounted socket still grants the launcher process control of the Docker
Engine. This service must stay separate from learner containers.

GHCR pulls assume anonymously accessible packages in the container. For private
packages use a deliberate Docker credential configuration, or run the Python
launcher on the host with its authenticated Docker CLI. There is no registry
sign-in form or secret storage in the browser. Registry mode requires a checkout
for the Compose definitions; it is not a server-side package discovery service.

## Publishing and validation

The shared release workflow validates Build4Fun and the addons before a single
seven-image publishing matrix runs. Build4Fun keeps its existing image path.
All jobs use the same prepared source revision. Stable releases update version
and `latest` tags; prereleases update only the version tag. Manual dispatch can
publish an explicit version from a selected branch, optionally updating `latest`.
Image-scoped Buildx caches avoid sharing incompatible build caches. Builds target
Linux AMD64 and ARM64. See [publishing images](../releases.md) for operation and image paths.

Unit tests exercise every service mapping, build removal, preserved settings,
action/tag validation, conflicting jobs, non-destructive stop, failure reporting,
Compose status formats, and HTTP Host/Origin checks. Browser tests use fixture
actions to verify local/GHCR choice, tag forwarding, activity, app links, and
responsive views. `docker_smoke.py` actually starts an isolated Build4Fun project,
checks HTTP, and stops it; `--registry` also pulls the released GHCR image. Its
project and workspace are independent of the normal learning stacks.

## Architecture selection

Each app card requires an explicit ARM64 or AMD64 selection before starting.
The info dialog explains common devices, the 64-bit Raspberry Pi OS requirement,
and emulation. `POST /api/action` validates `architecture` for start actions;
stopping remains available without an architecture selection.

The manager writes `platform: linux/<selection>` on every service for both local
builds and GHCR launches. Local mode uses a generated configuration preserving
absolute build contexts and mounts. Registry mode inspects each distinct image
and rejects a missing selected architecture before pulling. There is no automatic
fallback. New release images include both architectures; older AMD64-only tags
require explicit AMD64 selection and compatible emulation on ARM64 hosts.
