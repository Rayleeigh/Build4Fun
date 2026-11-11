# Naming and colour convention

The learning applications share the **<Activity>4Fun** naming pattern. Use the
capitalization shown below in interfaces and documentation, and lowercase full
names for technical identifiers.

| Application | Short name | Identity colour | Learning purpose |
| --- | --- | --- | --- |
| Build4Fun | B4 | Blue · `#0000B4` | Assemble and understand application environments. |
| Code4Fun | C4 | Green · `#00C400` | Build a frontend progressively with HTML, CSS, JavaScript, and a prepared API. |
| Crack4Fun | C4 | Red · `#C40000` | Solve filesystem, forensics, network-analysis, and web/API CTF programs. |

## Relationship between names and colours

The colours encode the application's short name in a six-digit RGB hex value.
`B4` occupies the blue pair for Build4Fun. `C4` occupies the green pair for
Code4Fun and the red pair for Crack4Fun. Unused channel pairs are `00`.

Code4Fun and Crack4Fun intentionally share the short name C4. Use their full
names wherever the short name would be ambiguous, including navigation,
documentation links, and technical identifiers. Colour supports recognition;
labels must also identify the application without relying on colour alone.

## Applying the colours

Use the identity colour for accents such as progress indicators, selections,
and primary actions. Keep the neutral surfaces and typography consistent across
the application family. Use darker related greens, reds, or blues where needed
for readable text, button labels, and interaction states; the base identity hex
remains the value in the table. Preserve semantic colours for errors and success
rather than making every status match the application's identity.

Build4Fun uses its blue accent and Code4Fun uses its green accent. Crack4Fun's
red is used for its interface accents.

## Crack4Fun naming

**Crack4Fun replaces the planned name Hack4Fun.** Its theme is **“Crack the
clues”**, and its description is **“Beginner web puzzles and capture-the-flag
challenges.”**

Apprentices follow clues through four programs: Filesystem (simple), Forensics
(simple to advanced), Network Analysis (simple), and Web/API (simple). Forensics
includes real offline dictionary cracking of a deliberately weak fictional
account hash using RockYou, along with hex-dump and artifact analysis. Other
programs cover Linux files, prepared packet captures, websites, and API requests.

The theme remains "Crack the clues." The scope now includes supplied hash
cracking exercises; it does not imply attacks on outside systems. See the
[program and file plan](crack4fun/files-plan.md) for artifacts and the `{FLAG}`
brace-only flag convention.

Use `crack4fun` for application identifiers and `docs/crack4fun/` for application
documentation. Runtime files live in `apps/crack4fun/` and public challenge catalogs
in `challenges/crack/`. The former Hack4Fun placeholders have been renamed.
