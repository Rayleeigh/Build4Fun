# Code4Fun learning path

`stages.json` defines the instructions, progressive hints, and visible checklist
for the six stages of one My Server Dashboard project. `starter/` supplies the
initial `index.html`, `style.css`, and `script.js`. Files are copied only when a
project is first created or the entire project is explicitly reset.

Hints contain a title, explanation, language label, code example, and a
"Your turn" adaptation prompt. Examples teach individual concepts using a
different page or API field, rather than providing complete dashboard solutions.
The workspace renders snippets as literal text, not executable HTML.

Stage checks live in `apps/code4fun/workspace/checks.py`. They evaluate rendered
HTML, computed styles, interactions, and API behavior in Chromium. The element
IDs and timing requirements are stated in the lesson instructions. Change the
checks and reference solution in `apps/code4fun/tests/fixtures/` together when
changing a checkpoint contract. Instruction text alone cannot define a new check.

The Build4Fun challenge catalog does not load these lessons. See the
[Code4Fun guide](../../apps/code4fun/README.md) for launch and verification commands.
