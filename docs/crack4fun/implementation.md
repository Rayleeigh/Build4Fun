# Crack4Fun implementation

## Runtime

`compose.crack4fun.yaml` launches six services: `workspace`, `filesystem`,
`forensics`, `network`, `web-terminal`, and `portal`. Images belong to
`apps/crack4fun/`; the shared sandbox image serves four separate containers.
The controller and portal use Python's standard-library HTTP server. The
workspace starts with a small volume ownership initializer, then drops to UID
65532 with a read-only root filesystem. The portal runs as UID 65532.

The browser uses a vendored, MIT-licensed xterm.js 5.5.0 terminal. Input and
cursor-based output polling pass through the controller to a root-owned agent
which creates an actual PTY, dropping its Bash child to UID/GID 1000. Each
program keeps its own terminal. Restore files terminates the program's sessions.
The Filesystem exercise permits `su` to root; the others enable no-new-privileges.

The controller has a UI network and individual internal control networks. Its
HTTP socket binds only the UI address. An apprentice cannot use the shared
control-network connection to call the controller's management API. Each agent
has its own bearer token, exposed only through a private named volume; other
programs are not on that agent's network. The portal has a separate private
control token and public HTTP listener. Host/Origin checks protect browser writes.
This arrangement is intended for a local session, not public multi-user hosting.

## Catalog, evidence, and verification

`challenges/crack/*/program.json` holds public task text, hints, difficulty, and
challenge identifiers. It has no answers. `workspace/programs.py` loads it.
`workspace/progress.py` creates a random persistent session secret, derives each
flag from HMAC-SHA256 of the challenge ID, and compares submissions in constant
time. Flag values use a 16-hex-digit digest suffix and brace-only syntax.
Writes replace the session file atomically. Repeated valid submissions do not
create a second completion or success notification.

`workspace/server.py` sends each agent only its own program's flags during
initialization. `sandbox/artifacts.py` generates evidence inside that container;
`portal/server.py` builds the corresponding web/API responses. The root-owned
agent state records initialization, and evidence is read-only to the normal
learner. The controller offers an explicit allowlist of evidence downloads;
it does not expose arbitrary agent paths. Flags intentionally exist in the
challenge evidence, never in a public answer catalog.

Forensics uses Pillow, ExifTool, real ZIP tools, binutils, xxd, and John.
Network artifacts are generated offline using Scapy with explicit Ethernet
addresses and documentation IP ranges; no live traffic is captured. Tshark
and Wireshark can reassemble the split HTTP responses.

## Dependencies and provenance

The sandbox Dockerfile pins John to commit
`37bebbe4b6442c8dd3888e5848ef062c0783e9f3` from the
[official repository](https://github.com/openwall/john). It builds CPU-only,
without OpenCL or native CPU tuning. John documentation ships in
`/usr/share/doc/john`; its wrapper keeps recovery files in the apprentice's home.

`prepare_wordlist.py` downloads the unmodified RockYou archive from
[SecLists](https://github.com/danielmiessler/SecLists/tree/64b41f2156e1ae3edb592535c1b4b4dd0d6fe26a/Passwords/Leaked-Databases),
pinned to revision `64b41f2156e1ae3edb592535c1b4b4dd0d6fe26a`. It records the
extracted file's checksum and line count. No wordlist or build products enter
Git. The exercise deliberately chooses an early real dictionary entry. Pillow
and Scapy versions are pinned in the sandbox requirements. The UI terminal's
license is retained beside the vendored assets.

## Validation

Unit checks cover flag syntax, uniqueness, scoped clearing, duplicate
submissions, persistence, and exclusion of secrets from public state.
`tests/container_smoke.py` provisions a separate Compose project, solves every
exercise with real tools, exercises PTY password elevation, checks protected
files and cross-program isolation, tests Host/Origin and download boundaries,
restores evidence, restarts the controller, and checks the browser at desktop
and mobile sizes. Its volumes are independent of the regular learner stack.

## Guided introduction

The workspace has an eleven-step first-run tutorial: CTF basics, flag format,
basic shell commands, course overview, then a tour anchored to actual interface
components. A native modal provides focus containment and Escape handling.
The guide repositions alongside highlighted controls, opens the sidebar on
small screens, and restores the previous navigation and hint state on exit.
Short position/content transitions respect reduced-motion preferences.

`POST /api/tutorial` records completion in the session volume, independently of
challenge progress. Existing sessions default to unseen without migration.
The toolbar can replay the guide. Browser checks cover completion, skipping,
reload persistence, keyboard focus, all guided stops, and mobile positioning.
