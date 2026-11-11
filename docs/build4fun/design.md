# Build4Fun interface

Build4Fun uses a restrained desktop workspace inspired by native Apple tools:
clear hierarchy, system typography, neutral working surfaces, grouped controls,
and subtle translucency. It remains a visual Docker Compose builder for
apprentices. The [naming and colour convention](../naming-and-colours.md) assigns
its blue identity accent `#0000B4`; Code4Fun keeps its green identity.

## Surfaces and hierarchy

The sidebar and toolbar use a small amount of glass. Menus, forms, and the block
inspector use the same translucent material. Code, service configuration, project
lists, and forms' input fields retain stable, readable working backgrounds.
Browsers without backdrop filtering receive solid surfaces. Increased-contrast
and reduced-transparency preferences also switch glass to opaque backgrounds.

System, Light, and Dark appearance remain available through the sidebar's
appearance control. Challenge pages follow the saved appearance preference,
including changes from another workspace tab. Dark appearance uses lighter
related accent text while primary actions retain the identifying blue.

Repeated workspace labels and decorative brand tiles have been removed from the
visible hierarchy. Project names, section headings, and service names carry the
structure. Compact rows, thin separators, and restrained corner radii distinguish
controls without making every configuration item a separate card.

## Navigation and actions

Projects use a grouped list with explicit Open, Rename, and Delete actions.
The sidebar retains project switching, file navigation, and the contextual block
palette. The builder keeps its composing area, linked Compose preview, and
inspector. The existing responsive layouts collapse navigation and expose a
separate YAML view on smaller screens.

Network map and Environment are grouped as project views. Validate, saved
versions, and YAML visibility remain directly available. Deploy is the primary
builder action and sits at the end of the action group. Deployment review and
confirmation behavior are unchanged.

The challenge page separates progress and project selection from lesson content.
Build instructions and configuration checks remain visible; Explain it and Try it
for real expand individually. Progress continues to reflect current saved
projects and refresh automatically.

## Interaction and verification

Controls keep native keyboard focus, existing accessible names, and clear
validation feedback. Hover actions remain available on keyboard focus and on
touch devices. Existing short arrival transitions respect reduced-motion settings.

The refactor changes presentation and navigation grouping. It does not change
project persistence, block validation, generated Compose output, Docker ownership,
or deployment execution. Code4Fun's autosave and tutorial features are not added
to Build4Fun by this change.

Unit and browser checks cover the builder, file editing, project management,
draft recovery, deployment review, responsive layouts, theme switching, challenge
disclosures, shared appearance preferences, and the higher-contrast glass fallback.
See the [user guide](../../apps/build4fun/README.md#checks) for commands.
