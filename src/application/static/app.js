'use strict';
const $ = id => document.getElementById(id);
let definitions, project, selected, files = [], sidebarMode = 'blocks', view = 'canvas';
let projectDirty = false, revision = 0, filePath = '', drag = null, undoSnapshot = null;
let canvasScroll = 0, saving = false;
const drafts = new Map();
const collapsed = new Set();
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function button(text, action, className) {
  const node = el('button', text, className);
  node.type = 'button'; node.addEventListener('click', action); return node;
}
function message(text = '', error = false) {
  $('notice').textContent = text;
  $('notice').classList.toggle('error', error);
}
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Request failed.');
  return result;
}
function guarded(action) { return async () => { try { await action(); } catch (e) { message(e.message, true); } }; }
function dirty() { return projectDirty || [...drafts.values()].some(d => d.dirty); }
function status() {
  $('save-status').textContent = saving ? 'Saving…' : dirty() ? 'Unsaved changes' : 'All changes saved';
  $('save').disabled = saving || !dirty();
  $('file-tab').textContent = filePath ? `${filePath}${drafts.get(filePath)?.dirty ? ' •' : ''}` : 'File';
}
function changed() { projectDirty = true; revision++; status(); }
function allNodes(node = project) { return [node, ...(node.children || []).flatMap(allNodes)]; }
function parentOf(node) { return allNodes().find(n => n.children.includes(node)); }
function allowed(node, moving) {
  return (definitions[node.type].children || []).filter(type =>
    !definitions[type].single || !node.children.some(child => child !== moving && child.type === type));
}
function context() {
  let node = selected;
  while (!(definitions[node.type].children || []).length && parentOf(node)) node = parentOf(node);
  return node;
}
function makeBlock(type) {
  const d = definitions[type];
  return {id: crypto.randomUUID(), type, version: d.version, values: Object.fromEntries(
    (d.inputs || []).map(f => [f.key, f.type === 'boolean' ? false : ''])), children: []};
}
function checkpoint() {
  undoSnapshot = JSON.stringify(project); $('undo').disabled = false;
}
function focusBlock(node) {
  requestAnimationFrame(() => {
    const card = [...document.querySelectorAll('[data-block-id]')].find(c => c.dataset.blockId === node.id);
    if (!card) return;
    const input = card.querySelector('input, select');
    (input || card.querySelector('.select-block')).focus({preventScroll: true});
    card.scrollIntoView({behavior: 'smooth', block: 'nearest'});
  });
}
function addBlock(parent, type) {
  if (!allowed(parent).includes(type)) return;
  checkpoint();
  const block = makeBlock(type); parent.children.push(block); selected = block;
  collapsed.delete(parent.id); changed(); view = 'canvas'; message(); render(); focusBlock(block);
}
function selectBlock(node) {
  selected = node;
  document.querySelectorAll('[data-block-id]').forEach(card => card.classList.toggle('selected', card.dataset.blockId === node.id));
  renderSidebar();
}
function referenceNames(kind) {
  return project.children.filter(n => definitions[n.type].op === 'named' && definitions[n.type].target === kind)
    .map(n => n.values.name).filter(Boolean);
}
function fillChoices(input, options, value, placeholder = 'Choose…') {
  input.replaceChildren(new Option(placeholder, ''));
  for (const option of options) input.append(new Option(option, option));
  if (value && !options.includes(value)) input.append(new Option(`${value} (missing)`, value));
  input.value = value;
}
function installDrop(card, node) {
  card.addEventListener('dragover', event => {
    if (!drag) return;
    const moving = drag.id ? allNodes().find(n => n.id === drag.id) : null;
    if (!allowed(node, moving).includes(drag.type) || (moving && allNodes(moving).includes(node))) return;
    event.preventDefault(); event.stopPropagation();
    event.dataTransfer.dropEffect = moving ? 'move' : 'copy';
    document.querySelectorAll('.drop-target').forEach(c => c.classList.remove('drop-target'));
    card.classList.add('drop-target');
  });
  card.addEventListener('dragleave', event => {
    if (!card.contains(event.relatedTarget)) card.classList.remove('drop-target');
  });
  card.addEventListener('drop', event => {
    if (!drag) return;
    const moving = drag.id ? allNodes().find(n => n.id === drag.id) : null;
    if (!allowed(node, moving).includes(drag.type) || (moving && allNodes(moving).includes(node))) return;
    event.preventDefault(); event.stopPropagation(); card.classList.remove('drop-target');
    if (moving) {
      if (parentOf(moving) === node) return;
      checkpoint(); const parent = parentOf(moving);
      parent.children = parent.children.filter(n => n !== moving); node.children.push(moving);
      selected = moving; collapsed.delete(node.id); changed(); render(); focusBlock(moving);
    } else addBlock(node, drag.type);
    drag = null;
  });
}
function renderBlock(node, parent) {
  const d = definitions[node.type];
  const card = el('article', undefined, `block ${node.type === 'harness' ? 'harness' : ''}${node === selected ? ' selected' : ''}`);
  card.dataset.blockId = node.id;
  card.addEventListener('click', event => { event.stopPropagation(); if (!event.target.closest('button')) selectBlock(node); });
  card.addEventListener('focusin', event => { event.stopPropagation(); selected = node; });
  installDrop(card, node);
  const title = el('div', undefined, 'block-title');
  const left = el('div', undefined, 'title-left');
  if (parent) {
    const handle = el('span', '⠿', 'drag-handle'); handle.draggable = true; handle.title = 'Drag this block to another valid parent';
    handle.addEventListener('dragstart', event => { drag = {id: node.id, type: node.type}; event.dataTransfer.setData('text/plain', node.type); event.dataTransfer.effectAllowed = 'move'; });
    left.append(handle);
  }
  left.append(button(d.label, () => selectBlock(node), 'select-block'));
  if ((d.inputs || []).some(f => f.key === 'name')) left.append(el('span', node.values.name || '', 'block-summary'));
  title.append(left);
  const actions = el('div', undefined, 'block-actions');
  if (parent) {
    const index = parent.children.indexOf(node);
    for (const [label, offset] of [['↑', -1], ['↓', 1]]) {
      const move = button(label, () => {
        checkpoint(); [parent.children[index], parent.children[index + offset]] = [parent.children[index + offset], parent.children[index]];
        changed(); render(); focusBlock(node);
      });
      move.disabled = index + offset < 0 || index + offset >= parent.children.length;
      move.setAttribute('aria-label', `Move ${d.label} ${offset < 0 ? 'up' : 'down'}`); actions.append(move);
    }
    actions.append(button('Remove', () => {
      checkpoint(); parent.children = parent.children.filter(n => n !== node); selected = parent;
      changed(); render(); message(`${d.label} removed. Use Undo to restore it.`);
    }, 'remove-block'));
  }
  if (node.children.length) {
    const toggle = button(collapsed.has(node.id) ? 'Expand' : 'Collapse', () => {
      if (collapsed.has(node.id)) collapsed.delete(node.id); else collapsed.add(node.id);
      render();
    }); toggle.setAttribute('aria-expanded', !collapsed.has(node.id)); actions.append(toggle);
  }
  title.append(actions); card.append(title);
  if (collapsed.has(node.id)) { card.append(el('p', `${node.children.length} blocks inside`, 'muted')); return card; }
  const fields = el('div', undefined, 'fields');
  for (const f of d.inputs || []) {
    const label = el('label', f.label); let input;
    if (f.type === 'choice' || f.reference) {
      input = el('select');
      const refresh = () => fillChoices(input, f.reference ? referenceNames(f.reference) : f.choices, node.values[f.key]);
      refresh(); input.addEventListener('focus', refresh);
    } else {
      input = el('input'); input.type = f.type === 'boolean' ? 'checkbox' : f.type === 'integer' ? 'number' : 'text';
      if (input.type === 'checkbox') input.checked = node.values[f.key]; else input.value = node.values[f.key];
      if (f.min !== undefined) input.min = f.min;
      if (f.max !== undefined) input.max = f.max;
      input.placeholder = f.label;
    }
    input.addEventListener('input', () => {
      node.values[f.key] = input.type === 'checkbox' ? input.checked : input.value; changed();
      if (f.key === 'name') left.querySelector('.block-summary').textContent = input.value;
      // Structural undo must never discard subsequent field edits.
      undoSnapshot = null; $('undo').disabled = true;
    });
    label.append(input);
    if (f.file) {
      const chooser = el('select'); chooser.setAttribute('aria-label', 'Choose a project file');
      fillChoices(chooser, files.map(f => f.path), '', 'Choose workspace file or folder…');
      chooser.addEventListener('change', () => { if (chooser.value) { node.values[f.key] = chooser.value; input.value = chooser.value; undoSnapshot = null; $('undo').disabled = true; changed(); } });
      label.append(chooser, button('Open file', guarded(() => openFile(node.values[f.key]))));
    }
    fields.append(label);
  }
  if ((d.inputs || []).length) card.append(fields);
  const help = el('details', undefined, 'block-help'); help.append(el('summary', 'What does this do?'), el('p', d.help)); card.append(help);
  const children = el('div', undefined, 'children');
  for (const child of node.children) children.append(renderBlock(child, node));
  card.append(children);
  const available = allowed(node);
  if (available.length) {
    const row = el('div', undefined, 'add-row');
    available.forEach(type => row.append(button(`+ ${definitions[type].label}`, () => addBlock(node, type), 'add-chip')));
    card.append(row);
  }
  return card;
}
function createForm(folder = false) {
  const form = el('form', undefined, 'create-form');
  const label = el('label', folder ? 'Folder path' : 'File path');
  const input = el('input'); input.required = true; input.placeholder = folder ? 'config' : 'config/dnsmasq.conf'; label.append(input);
  const submit = el('button', 'Create'); submit.type = 'submit';
  form.append(label, submit, button('Cancel', renderSidebar));
  form.addEventListener('submit', event => {
    event.preventDefault();
    guarded(async () => {
      submit.disabled = true;
      try {
        const path = input.value.trim();
        await api(folder ? '/api/folder' : '/api/file', folder ? {path} : {path, content: '', create: true});
        files = await api('/api/files');
        if (folder) renderSidebar(); else await openFile(path);
      } finally { submit.disabled = false; }
    })();
  });
  $('sidebar').prepend(form); input.focus();
}
function renderSidebar() {
  $('show-blocks').setAttribute('aria-pressed', sidebarMode === 'blocks');
  $('show-files').setAttribute('aria-pressed', sidebarMode === 'files');
  const area = $('sidebar'); area.replaceChildren();
  if (sidebarMode === 'blocks') {
    const parent = context();
    area.append(el('p', 'ADD BLOCKS', 'eyebrow'), el('strong', definitions[parent.type].label));
    area.append(el('p', 'Click to add here, or drag a block into a matching container.', 'muted'));
    if (parent !== project) area.append(button('← Project blocks', () => { selected = project; view = 'canvas'; render(); }));
    allowed(parent).forEach(type => {
      const b = button(`+ ${definitions[type].label}`, () => addBlock(parent, type), 'palette-block');
      b.title = definitions[type].help; b.draggable = true;
      b.addEventListener('dragstart', event => { drag = {type}; event.dataTransfer.setData('text/plain', type); event.dataTransfer.effectAllowed = 'copy'; });
      area.append(b);
    });
    if (!allowed(parent).length) area.append(el('p', 'All available sections have been added.', 'muted'));
  } else {
    area.append(el('p', 'PROJECT FILES', 'eyebrow'));
    const actions = el('div', undefined, 'file-actions');
    actions.append(button('+ File', () => { renderSidebar(); createForm(); }), button('+ Folder', () => { renderSidebar(); createForm(true); })); area.append(actions);
    if (!files.length) area.append(el('p', 'Add the files your services need. You can attach them with a Bind mount block.', 'muted'));
    files.forEach(f => {
      const entry = f.directory ? el('p', `▾ ${f.path}/`, 'file-entry directory') : button(f.path, guarded(() => openFile(f.path)));
      entry.classList.add('file-entry'); if (f.path === filePath) entry.classList.add('active-file'); area.append(entry);
    });
  }
}
async function openFile(path) {
  if (!path) throw new Error('Choose or enter a project file path first.');
  if (!drafts.has(path)) {
    const result = await api(`/api/file?path=${encodeURIComponent(path)}`);
    drafts.set(path, {content: result.content, dirty: false, revision: 0, caret: 0, scroll: 0});
  }
  if (view === 'canvas') canvasScroll = window.scrollY;
  filePath = path; view = 'file'; sidebarMode = 'files'; message(); render();
}
async function saveAll() {
  if (saving) return;
  saving = true; status();
  try {
    if (projectDirty) {
      const currentRevision = revision;
      await api('/api/project', {project});
      if (revision === currentRevision) projectDirty = false;
    }
    for (const [path, draft] of drafts) {
      if (!draft.dirty) continue;
      const currentRevision = draft.revision;
      await api('/api/file', {path, content: draft.content});
      if (draft.revision === currentRevision) draft.dirty = false;
    }
    message(dirty() ? 'Saved. Newer edits are still unsaved.' : 'All changes saved.');
  } finally { saving = false; status(); }
}
function switchView(next) {
  if (view === 'canvas') canvasScroll = window.scrollY;
  view = next; message(); render();
  if (view === 'canvas') window.scrollTo({top: canvasScroll});
}
function render() {
  renderSidebar(); status();
  $('canvas-tab').setAttribute('aria-pressed', view === 'canvas');
  $('preview-tab').setAttribute('aria-pressed', view === 'preview');
  $('file-tab').hidden = !filePath;
  $('file-tab').setAttribute('aria-pressed', view === 'file');
  const content = $('content'); content.replaceChildren();
  if (view === 'canvas') {
    content.append(el('h1', 'Build your environment'), el('p', project.children.length ? 'Add configuration where it belongs. Each block describes one part of your environment.' : 'Start with a project name, then add your first service. You choose what it runs.', 'intro'), renderBlock(project));
  } else if (view === 'file') {
    const draft = drafts.get(filePath);
    content.append(el('h1', filePath));
    const editor = el('textarea'); editor.value = draft.content; editor.spellcheck = false;
    editor.setAttribute('aria-label', `Edit ${filePath}`);
    editor.addEventListener('input', () => { draft.content = editor.value; draft.dirty = true; draft.revision++; status(); });
    const remember = () => { draft.caret = editor.selectionStart; draft.scroll = editor.scrollTop; };
    editor.addEventListener('keyup', remember); editor.addEventListener('click', remember); editor.addEventListener('scroll', remember); editor.addEventListener('blur', remember);
    content.append(editor, el('small', 'Your edits stay here while you switch views. Save all or Ctrl/Cmd+S writes them to disk.'));
    editor.setSelectionRange(draft.caret, draft.caret); editor.scrollTop = draft.scroll;
  } else {
    content.append(el('h1', 'Compose preview'), el('p', 'Generated from your blocks. Return to Build to make changes.', 'intro'));
    const pre = el('pre', 'Generating…'); content.append(pre);
    const previewRevision = revision;
    api('/api/preview', {project}).then(result => {
      if (view !== 'preview' || revision !== previewRevision || !pre.isConnected) return;
      pre.textContent = result.yaml;
      content.append(button('Download compose.yaml', () => {
        const url = URL.createObjectURL(new Blob([result.yaml], {type: 'application/yaml'}));
        const a = el('a'); a.href = url; a.download = 'compose.yaml'; a.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }));
    }).catch(error => {
      if (!pre.isConnected) return;
      pre.classList.add('preview-error'); pre.textContent = error.message;
      content.append(button('← Continue building', () => switchView('canvas')));
    });
  }
}
$('save').onclick = guarded(saveAll);
$('undo').onclick = () => {
  if (!undoSnapshot) return;
  project = JSON.parse(undoSnapshot); selected = project; undoSnapshot = null; $('undo').disabled = true;
  changed(); render(); message('Last block change undone.');
};
$('show-blocks').onclick = () => { sidebarMode = 'blocks'; renderSidebar(); };
$('show-files').onclick = () => { sidebarMode = 'files'; renderSidebar(); };
$('canvas-tab').onclick = () => switchView('canvas');
$('file-tab').onclick = () => switchView('file');
$('preview-tab').onclick = () => switchView('preview');
document.addEventListener('dragend', () => { drag = null; document.querySelectorAll('.drop-target').forEach(c => c.classList.remove('drop-target')); });
window.addEventListener('beforeunload', event => { if (dirty()) { event.preventDefault(); event.returnValue = ''; } });
document.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault(); guarded(saveAll)();
  }
});
guarded(async () => {
  [definitions, project, files] = await Promise.all([api('/api/definitions'), api('/api/project'), api('/api/files')]);
  selected = project; render();
})();
