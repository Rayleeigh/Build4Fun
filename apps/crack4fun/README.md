# Crack4Fun

A local, hands-on CTF workspace for one apprentice. Four independent programs
follow connected evidence trails in the fictional Apprentice Portal:

| Program | Level | Flags |
| --- | --- | --- |
| Filesystem | Simple | 4 |
| Forensics | Simple → Advanced | 6 |
| Network Analysis | Simple | 3 |
| Web/API | Simple | 4 |

## Run

From the repository root, with Docker Engine and Compose installed:

```sh
docker compose -f compose.crack4fun.yaml up --build -d --wait
```

Open http://localhost:8100. The prepared portal is http://localhost:8101 and is
also available inside the workspace. Change `CRACK_HTTP_PORT` and
`CRACK_PORTAL_PORT` in `.env` to use other ports. Build4Fun and Code4Fun run
independently and can stay running.

The first build needs internet access and takes longer: it compiles a pinned
John the Ripper revision and downloads the full pinned RockYou wordlist.
Neither is committed to Git. Once built, the exercises run without internet.
Start with a program, follow its tasks, reveal hints as needed, and submit flags
including their braces, for example `{example_token}`. Progress saves immediately.
The terminal is a real Bash PTY, starting as `apprentice`, rather than simulated
command responses. Forensics and network evidence can also be downloaded for
inspection in desktop tools such as Wireshark.

## Interactive introduction

The first visit opens a guided tutorial, starting with CTFs, brace-only flags,
and basic terminal commands. It introduces the four programs, then highlights
the sidebar, tasks, hints, terminal, flag submission, progress, and reset controls.
Use Back, Next, or Skip tutorial; Escape also closes it. Tutorial completion is
saved with the learner session, so refreshing or changing browsers does not
restart it. Select **Tutorial** in the toolbar to replay it anytime. The guide
supports narrow screens, keyboard focus, and reduced-motion preferences.

Once the stack and scenario are ready, opening the terminal only creates a Bash
process and connects its PTY; there is no new container build for each terminal.
First image builds and Docker health checks are separate from terminal loading.
“Preparing…” means scenario setup is pending, “Connected” means the terminal is
available, and “Disconnected” indicates an error rather than an indefinite load.

## Exercises

Filesystem introduces hidden files, logs, planted shell history, `su`, and file
permissions. Only its sandbox deliberately permits the supplied root password.
Forensics combines hex decoding, file signatures, image metadata, ZIP carving,
CPU dictionary recovery of an unsalted SHA-256 hash, and log/CSV correlation.
The password is an early entry in the unmodified RockYou list, keeping the
exercise short without simulating cracking. `/wordlists/provenance.json` records
the source revision, SHA-256 digest, and line count. Network Analysis uses a
synthetic PCAP with DNS and split HTTP responses. Web/API uses a real website,
HTML and JavaScript clues, headers, query parameters, and a JSON POST request.

## Persistence and resets

The `workspace` named volume keeps the session secret and completion history.
Flags are unique to that session and stable across controller restarts.
**Restore files** restores the selected scenario and clears its scratch work;
it keeps flags and progress. **Clear progress** clears only that program's
completion history. Both require confirmation. Neither operation affects the
other applications.

Restore files is scenario restoration, not a fresh container. If a learner with
root damages the filesystem sandbox's OS or control agent, recreate that service
and restart the controller to initialize it again:

```sh
docker compose -f compose.crack4fun.yaml up -d --force-recreate filesystem
docker compose -f compose.crack4fun.yaml restart workspace
```

Stop with `docker compose -f compose.crack4fun.yaml stop`. A normal `down` keeps
progress volumes; adding `--volumes` deletes the saved session and its flags.

## Boundaries

This version serves one trusted local apprentice per stack, not multiple users
on a public server. Ports bind to loopback. Four separate learner containers have
separate internal networks; the portal joins only the web program. The controller
binds its management API exclusively to its UI network and authenticates agent
requests with separate private tokens. Learners receive no Docker socket or host
filesystem mounts. Resource limits apply to the containers. Root inside the
Filesystem exercise can control that exercise's container; containers share the
host kernel, so this is not a hostile multi-tenant isolation guarantee.

## Checks

```sh
python -m unittest discover -s apps/crack4fun/tests -v
# Install Playwright and Chromium as described in the repository checks workflow.
python apps/crack4fun/tests/container_smoke.py
```

The integration check builds its own isolated Compose project, solves all 17
flags with actual tools, tests the root PTY exercise and network boundaries,
checks persistence and restoration, and exercises desktop/mobile browser views.
It removes only its own containers and volumes afterward.

See [implementation](../../docs/crack4fun/implementation.md),
[course plan](../../docs/crack4fun/files-plan.md), and
[challenge catalog](../../challenges/crack/README.md).
