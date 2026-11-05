# Repository architecture

Build4Fun, Code4Fun, and Hack4Fun live in one repository with separate application
directories. Build4Fun is the existing runnable application; the other two are
planned addons with documented locations for future implementation.

| Location | Responsibility |
| --- | --- |
| `apps/build4fun/application/` | Existing Python backend and browser interface |
| `apps/build4fun/templates/` | Compose block definitions |
| `apps/build4fun/tests/` | Build4Fun unit, browser, and Docker checks |
| `apps/code4fun/` | Future interactive coding workspace |
| `apps/hack4fun/` | Future beginner CTF interface and sessions |
| `challenges/build/` | Existing Compose lessons and configuration checks |
| `challenges/code/` | Future coding lessons and behavior checks |
| `challenges/hack/` | Future CTF scenarios and flag verification |
| `docs/monorepo.md` | Shared repository architecture |
| `docs/build4fun/` | Build4Fun purpose, implementation, and images |
| `docs/code4fun/` | Code4Fun product and implementation planning |

Documentation follows the application boundaries: shared repository guidance
stays directly under `docs/`, and application-specific documents live under
`docs/<application>/`. Keep images with the documentation that uses them. Add
Hack4Fun documentation under `docs/hack4fun/` when its planning begins.

The [Code4Fun plan](code4fun/plan.md) defines one progressively developed server
dashboard, six frontend learning stages, and a separate prepared API container.

Run commands from the repository root. The root Dockerfile, Compose file,
requirements, and GitHub workflows continue to build and validate Build4Fun.
Existing workspace locations, environment variables, deployment ownership,
and public `/docs/challenges/` URLs remain compatible. Lesson files now live in
`challenges/build/`; only that directory feeds the current challenge catalog.

Shared functionality remains inside Build4Fun until another addon needs it.
Extract reusable project, challenge, or runtime code when its interface can be
validated against both consumers. Avoid importing application internals across
addon directories.

Repository boundaries do not define runtime isolation. Learner code and CTF
sandboxes must run separately from the controller, without its Docker access.
Individual sessions and stronger isolation are required before shared hosting.
Code4Fun, Hack4Fun, their browser terminal, and application behavior checks are
future implementation work, not features enabled by this reorganization.
