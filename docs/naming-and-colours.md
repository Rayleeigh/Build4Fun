# Naming and colour convention

The learning applications share the **<Activity>4Fun** naming pattern. Use the
capitalization shown below in interfaces and documentation, and lowercase full
names for technical identifiers.

| Application | Short name | Identity colour | Learning purpose |
| --- | --- | --- | --- |
| Build4Fun | B4 | Blue · `#0000B4` | Assemble and understand application environments. |
| Code4Fun | C4 | Green · `#00C400` | Build a frontend progressively with HTML, CSS, JavaScript, and a prepared API. |
| Crack4Fun | C4 | Red · `#C40000` | Explore beginner web puzzles and capture-the-flag challenges. |

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

These values define the shared convention. Code4Fun already uses its green
accent; this document does not imply that every existing Build4Fun control has
been recoloured. Crack4Fun's red applies when its interface is implemented.

## Crack4Fun naming

**Crack4Fun replaces the planned name Hack4Fun.** Its theme is **“Crack the
clues”**, and its description is **“Beginner web puzzles and capture-the-flag
challenges.”**

Apprentices explore prepared websites, inspect HTML, CSS, and JavaScript, use
curl to understand API endpoints, and retrieve flags. The name refers to solving
clues; password cracking, brute forcing, and breaking encryption are outside the
intended curriculum.

Use `crack4fun` for new application identifiers and `docs/crack4fun/` for future
application documentation. The existing placeholder directories
`apps/hack4fun/` and `challenges/hack/` retain their current paths until a separate
repository rename; they now refer to Crack4Fun. Documenting this convention does
not rename directories or change launch commands.
