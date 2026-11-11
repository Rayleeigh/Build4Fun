# Crack4Fun programs and file plan

Status: initial implementation available. This document records the course
design; see [implementation](implementation.md) for the actual runtime and
[setup](../../apps/crack4fun/README.md) for launch and reset commands.
The implementation uses six services, four real PTY terminals, session-derived
flags, and offline-generated evidence.

## Course structure

Crack4Fun contains four CTF programs in the same fictional organization,
**the Apprentice Portal**. Each program has its own connected evidence trail,
instructions, progressively revealed hints, and separately recorded progress.
Programs can be started independently; completing Filesystem is not a prerequisite
for Forensics, Network Analysis, or Web/API.

| Program | Difficulty | Flags | Focus |
| --- | --- | --- | --- |
| Filesystem | Simple | 4 | Shell navigation, hidden files, permissions, and misplaced credentials |
| Forensics | Simple → Advanced | 6 | Hex dumps, signatures, metadata, embedded artifacts, weak hashes, and evidence correlation |
| Network Analysis | Simple | 3 | Hosts, protocols, HTTP conversations, and file extraction from a prepared capture |
| Web/API | Simple | 4 | Page inspection, JavaScript discovery, headers, query parameters, and JSON POST requests |

The initial implementation provides all 17 flags. Artifact sketches below describe the course design; exact runtime paths are documented in each task. Advanced
means advanced within this apprentice course: combining tools and evidence, not
requiring malware analysis, memory forensics, or attacks on outside systems.

## Flag format and verification

Use **`{FLAG}`** syntax: a token enclosed in one pair of literal braces, with no
prefix. For example, `{hidden_in_plain_sight}` is a demonstration of the syntax,
not a real challenge answer. This is the Crack4Fun convention; CTF flag formats
are not universal.

- Payloads contain lowercase ASCII letters, digits, and underscores: `\{[a-z0-9_]+\}`.
- Each challenge has a distinct flag. Never use the literal `{FLAG}` as an answer.
- Submissions trim surrounding whitespace, then require a full, case-sensitive
  match. Do not strip braces or search arbitrary pasted text for a matching substring.
- Validate against the selected challenge and record completion idempotently.
  A repeated correct submission reports already completed rather than awarding twice.
- The browser receives challenge descriptions and completion state, not expected
  answers or a complete answer catalog. Submission format errors and incorrect
  answers receive useful feedback without disclosing the expected value.

The generator substitutes flags into artifacts and supplies verification records
to the workspace separately. Use per-session values where practical. The evidence
bundle and verifier must belong to the same session; regenerating one without
updating the other would make valid solutions fail.

## Filesystem · Simple

Story: inspect a workstation left behind by a previous administrator. Start as
`apprentice` in a real Linux shell. The root password is a deliberately planted
training credential, valid only inside this program's disposable container.

```text
/home/apprentice/
├── README.txt
├── .bash_history
├── notes/
│   └── handover.txt
└── documents/
    ├── inventory.txt
    └── .maintenance-note
/var/log/portal/
└── maintenance.log
/root/
├── flag.txt
└── closure-note.txt
/tmp/                             # Scratch files
```

| ID | Artifact and intended trail | Tools | Learning objective |
| --- | --- | --- | --- |
| fs-01 | README points to the hidden maintenance note containing a flag | pwd, ls -la, cat | Find hidden files and understand paths |
| fs-02 | Handover identifies a maintenance event; its log entry contains a flag | find, grep, less | Locate relevant files and filter text |
| fs-03 | Readable shell history exposes the root credential; `/root/flag.txt` holds the flag | history file inspection, su, id, cat | Understand users, file permissions, and credential leakage |
| fs-04 | Root's closure note identifies a particular record in inventory.txt | cat, grep | Follow and combine clues across files |

`/root` is root's home directory; `/` is the filesystem root. Make this distinction
explicit in the lesson. Retain an original history seed separately from ongoing
shell history so logging out does not erase the starting clue.

The root-access exercise comes near the end. Once root is obtained, all files in
that container are readable. Treat these as suggested learning steps rather than
strictly enforced ordering, and never store other programs' private data there.

## Forensics · Simple to advanced

Story: recover evidence from an exported incident bundle. Provide immutable
original evidence and a writable working directory. Each recovered artifact or
note points to the next task.

```text
/evidence/forensics/
├── README.txt
├── checksums.sha256
├── 01-message.hex
├── 02-recovered.dat
├── 03-workshop-photo.jpg
├── 04-support-bundle.bin
├── 05-account.sha256
└── 06-records.zip
/work/forensics/                    # Apprentice copies and extracted files
/wordlists/
└── rockyou.txt                     # Provisioned wordlist, not committed to Git
```

| ID | Level | Artifact and intended trail | Tools | Learning objective |
| --- | --- | --- | --- | --- |
| fo-01 | Simple | A short hex dump includes the flag's ASCII bytes | xxd, less | Relate hex bytes to text; read both dump columns |
| fo-02 | Simple | recovered.dat has a recognizable file signature; inspect the real file type to recover a flag | file, xxd | Trust content signatures rather than extensions |
| fo-03 | Intermediate | A JPEG metadata field contains a flag and a clue about the support bundle | exiftool | Separate metadata from visible image content |
| fo-04 | Intermediate | The support bundle contains an embedded archive, with a flag and an account note inside | strings, xxd, binwalk or documented offsets, unzip | Identify and extract embedded evidence |
| fo-05 | Advanced | Recover the deliberately weak password represented by account.sha256 using RockYou; it opens records.zip, whose recovery note contains the flag | John the Ripper Jumbo, rockyou.txt, archive extraction | Perform a real offline dictionary attack against a supplied fast, unsalted hash |
| fo-06 | Advanced | Correlate timestamps and record IDs in the unlocked archive to identify the record containing the final flag | less, grep, sort, a text editor | Combine evidence instead of merely extracting another file |

### Password exercise contract

The account is fictional. `05-account.sha256` contains a real SHA-256 digest of
a weak password present in the supplied RockYou wordlist. The recovered password
is an archive credential, not itself the flag; the flag is inside the artifact
it unlocks. This makes successful recovery observable.

Use a CPU-capable John the Ripper Jumbo build with raw SHA-256 support. GPU access
and Hashcat are not required for completion. Select a password occurring early in
the provisioned wordlist, and measure recovery time on the minimum supported
laptop before fixing the exercise. Target a few minutes rather than hours.

The unlocked ZIP is a teaching artifact supported by the installed extraction
tool. Its purpose is to demonstrate using the recovered credential, not to add
an unplanned second cracking task. Explain why a fast, unsalted general-purpose
hash and a weak password are inappropriate for password storage.

Provision a known RockYou file outside Git and record its source, checksum,
encoding, and exact selected password's membership in instructor-side generation
metadata. Do not silently truncate or rewrite it. A smaller practice subset can
be an explicitly labelled optional mode, not a substitute for the main exercise.
The generator must never place the chosen password in the learner manifest or
terminal environment variables. Define distribution/provisioning before builds
so the exercise works without downloads during the learner session.

## Network Analysis · Simple

Story: analyze a recorded support session. Work from a synthetic PCAP with a
small number of fictional hosts and deliberate plaintext HTTP traffic. No live
network interception is needed.

```text
/evidence/network-analysis/
├── README.txt
├── topology.txt
├── support-session.pcap
└── capture.sha256
/work/network-analysis/
```

| ID | Artifact and intended trail | Tools | Learning objective |
| --- | --- | --- | --- |
| net-01 | Find the DNS query and response identifying the portal host; the hostname includes a clue leading to a flag-bearing HTTP response | tshark; Wireshark optional | Identify hosts, DNS, and the destination service |
| net-02 | Follow the indicated HTTP conversation; a response header carries a flag | tshark stream following or Wireshark Follow TCP Stream | Distinguish request/response headers and bodies |
| net-03 | Export a small text file transferred in that conversation; it contains the final flag | tshark HTTP object export or Wireshark Export Objects | Reassemble an artifact rather than inspect isolated packets |

Keep captures short and valid, including the traffic needed for stream reassembly.
Use invented domains and documentation IP ranges. The browser terminal supplies
tshark; downloadable PCAP files allow optional use of desktop Wireshark.
These lessons must explain that encrypted HTTPS traffic cannot generally be read
like the deliberately plaintext HTTP capture in this program.

## Web/API · Simple

Story: inspect the organization's Apprentice Portal and work through its exposed
interfaces. The portal runs in its own container, separate from the shell.

```text
/app/
├── server.py
├── public/
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── private/
    ├── archive.json
    └── dispatch.json
```

| ID | Artifact and intended trail | Tools | Learning objective |
| --- | --- | --- | --- |
| web-01 | A comment in the homepage contains a flag and points to a hidden notice | Browser page source, curl | Inspect HTML beyond rendered content |
| web-02 | CSS hides the notice; it holds a flag and points toward the JavaScript request logic | Browser inspector, CSS source | Understand presentation and visibility |
| web-03 | JavaScript and GET `/api/info` describe a required header and archive filter; GET `/api/archive?department=training` with that header returns a flag and the next clue | Browser Network panel, curl | Discover endpoints, query parameters, headers, and JSON |
| web-04 | POST `/api/dispatch` with JSON describing a supported training-kit action returns the final flag | curl | Use a method, Content-Type, structured body, and response status correctly |

The implemented header is `X-Archive-Key: workshop-handover`. Dispatch expects
`{"parcel":"training-kit","action":"release"}` with `application/json`.
`/api/info` documents the contract. The initial portal serves its HTML/CSS/JS
from explicit routes in `portal/server.py` and keeps provisioned values in
`/state/portal.json`, never in a static private directory.

## Application and repository files

The implemented layout follows app-owned builds and a root Compose file:

```text
compose.crack4fun.yaml
apps/crack4fun/
├── Dockerfile
├── workspace/
│   ├── entrypoint.py               # Initialize volume ownership, drop privileges
│   ├── server.py                   # UI, verification, agent proxy, downloads
│   ├── programs.py                 # Load public catalogs
│   ├── progress.py                 # Persistent session and HMAC flags
│   └── static/                     # #C40000 accent, vendored xterm.js
├── sandbox/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── agent.py                    # Authenticated provisioning and PTY service
│   ├── artifacts.py                # Scenario generation
│   ├── prepare_wordlist.py
│   └── john-wrapper.py
├── portal/
│   ├── Dockerfile
│   └── server.py
└── tests/
    ├── test_progress.py
    └── container_smoke.py          # Real solve paths and browser checks
challenges/crack/
├── filesystem/program.json
├── forensics/program.json
├── network-analysis/program.json
└── web-api/program.json
```

Each catalog includes the instructions and progressive hints directly. It must
never contain expected flag values or recovered passwords. Generated binaries,
archives, captures, and the full RockYou file live in containers, not Git.
The shared sandbox image supplies all course tools, but four distinct containers
and internal networks separate the programs. The UI does not install tools.

## Sessions and reset

The initial implementation runs one local apprentice session per Compose stack.
Browser terminals use real PTYs and HTTP input/output polling. Docker Compose
owns container lifecycle; the controller receives no Docker socket. The workspace
named volume persists the random session secret and progress. Each agent receives
only its own program's derived flags over authenticated internal HTTP.

Restore files restores scenario artifacts and clears scratch work separately
from clearing progress. Neither action resets other programs. Switching programs
preserves terminals and completions. Recreating a damaged sandbox is an instructor
Compose operation, documented in the [setup guide](../../apps/crack4fun/README.md).
Deleting the workspace volume deliberately creates a new session and new flags.

Forensics uses a real embedded ZIP, a ZipCrypto-encrypted archive, and the full
pinned SecLists RockYou file. The selected password is an early entry in that
unchanged list. A local CPU-only integration run recovered it in 0.35 seconds;
this measures the prepared exercise on the development machine, not a general
password-cracking benchmark. See [implementation](implementation.md) for pinned
revisions, runtime boundaries, and provenance details.

## Verification before release

- Generate every flag in the agreed brace-only syntax and verify unique values.
- Walk each intended solve path against the built images, not just source fixtures.
- Assert that instructor answers and other programs' private data are absent from
  learner images and browser catalog responses.
- Verify that both simple shell users and the exercise's container root remain
  within their intended program boundaries.
- Benchmark the supplied hash and exact provisioned wordlist on CPU-only hardware.
- Check PCAP reassembly, exported objects, metadata retention, and archive passwords.
- Exercise flag submission, duplicate completion, progress persistence, switching,
  and both reset actions through the browser.
