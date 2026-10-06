'use strict';
/* The model remains the same; these components only change how it is presented. */
const $ = id => document.getElementById(id);
const state = {
  filesExpanded: true, projectsExpanded: true, projects: [], activeProject: null, switching: false, definitions: {}, project: null, files: [], view: 'projects', pane: null, selected: null,
  runtimeBusy: false, runtimeOutput: '', runtimeServices: [], previewVisible: true, revision: 0, dirty: false, saving: false, deleting: false, history: [], drafts: new Map(), file: '',
  collapsed: new Set(), folders: new Set(), touched: new Set(), issues: [], validated: null,
  arriving: new Set(), preview: null, previewRevision: -1, previewError: '', drag: null, ready: false
};
const projectSessions = new Map();
let previewTimer, previewRequest = 0, fileRequest = 0, noticeTimer, menuAnchor, formAnchor;
const paths = {
  cube: 'M12 3 3 8v9l9 5 9-5V8Z M3 8l9 5 9-5 M12 13v9 M7.5 5.5l9 5',
  build: 'M4 4h6v6H4z M14 4h6v6h-6z M4 14h6v6H4z M14 14h6v6h-6z',
  code: 'm8 7-5 5 5 5 m8-10 5 5-5 5 m-3-13-2 16',
  folder: 'M3 7V5h6l2 2h10v13H3Z',
  file: 'M5 3h9l5 5v13H5Z M14 3v6h5 M8 13h8 M8 17h6',
  network: 'M9 3h6v6H9z M3 16h6v5H3z M15 16h6v5h-6z M12 9v4 M6 16v-3h12v3',
  volume: 'M4 6c0-4 16-4 16 0s-16 4-16 0 M4 6v12c0 4 16 4 16 0V6 M4 12c0 4 16 4 16 0',
  image: 'M4 4h16v16H4z M4 16l5-6 4 4 3-3 4 5 M15 8h.01',
  ports: 'M4 7h14 m-4-4 4 4-4 4 M20 17H6 m4-4-4 4 4 4',
  environment: 'M8 4H5v16h3 M16 4h3v16h-3 M10 9h4 M10 15h4',
  mount: 'M8 3v6 M16 3v6 M5 9h14v3a7 7 0 0 1-14 0Z M12 19v3',
  plus: 'M12 5v14 M5 12h14', close: 'm6 6 12 12 M18 6 6 18',
  more: 'M5 12h.01 M12 12h.01 M19 12h.01', check: 'm5 12 4 4L19 6',
  chevron: 'm9 5 7 7-7 7', down: 'm5 9 7 7 7-7',
  sidebar: 'M3 4h18v16H3Z M9 4v16', split: 'M3 4h18v16H3Z M12 4v16',
  undo: 'M9 5 4 10l5 5 M4 10h9a6 6 0 0 1 0 12',
  warning: 'm12 3 10 18H2Z M12 9v5 M12 17h.01',
  download: 'M12 3v12 m-5-5 5 5 5-5 M4 16v5h16v-5',
  search: 'M16 10a6 6 0 1 1-12 0 6 6 0 0 1 12 0 m-2 4 6 6',
  theme: 'M20 14a8 8 0 0 1-10-10 8 8 0 1 0 10 10',
  edit: 'm4 16 12-12 4 4L8 20H4Z M13 7l4 4',
  trash: 'M3 6h18 M9 6V3h6v3 M5 6l1 15h12l1-15 M10 10v7 M14 10v7',
  copy: 'M8 8h12v13H8Z M16 8V3H3v13h5',
  up: 'm5 14 7-7 7 7', grip: 'M9 5h.01 M15 5h.01 M9 12h.01 M15 12h.01 M9 19h.01 M15 19h.01',
  info: 'M12 8h.01 M12 11v6 M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'
};
function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('class', 'icon'); svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(svg.namespaceURI, 'path'); path.setAttribute('d', paths[name] || paths.cube); svg.append(path); return svg;
}
function el(tag, text, className) {
  const node = document.createElement(tag); if (text !== undefined) node.textContent = text;
  if (className) node.className = className; return node;
}
function button(text, action, style = 'tertiary', glyph) {
  const node = el('button', undefined, `button ${style}`); node.type = 'button';
  if (glyph) node.append(icon(glyph)); node.append(el('span', text)); node.addEventListener('click', action); return node;
}
function iconButton(name, label, action) {
  const node = el('button', undefined, 'icon-button'); node.type = 'button'; node.title = label;
  node.setAttribute('aria-label', label); node.append(icon(name)); node.addEventListener('click', action); return node;
}
function blockIcon(type) {
  return ({service:'cube',image:'image',ports:'ports',port:'ports',environment:'environment',variable:'environment',mounts:'mount','volume-mount':'volume','bind-mount':'file','named-volume':'volume',network:'network','external-network':'network','network-configuration':'network','network-attachment':'network','project-name':'build'})[type] || 'cube';
}
function definition(node) { return state.definitions[node.type]; }
function nodes(node = state.project) { return node ? [node, ...node.children.flatMap(nodes)] : []; }
function find(id) { return nodes().find(n => n.id === id); }
function parentOf(node) { return nodes().find(n => n.children.includes(node)); }
function projectName() { return state.project?.children.find(n => n.type === 'project-name')?.values.name || 'Untitled project'; }
function nameOf(node) { return node.values.name || definition(node).label; }
function allowed(parent, moving) { return (definition(parent).children || []).filter(type => !state.definitions[type].single || !parent.children.some(n => n !== moving && n.type === type)); }
function makeBlock(type) { const d = state.definitions[type]; return {id: crypto.randomUUID(),type,version:d.version,values:Object.fromEntries((d.inputs || []).map(f => [f.key,f.type === 'boolean' ? false : ''])),children:[]}; }
function snapshot() { state.history.push(JSON.stringify(state.project)); if (state.history.length > 40) state.history.shift(); }
function dirty() { return state.dirty || [...state.drafts.values()].some(d => d.dirty); }
function changed() {
  state.dirty = true; state.revision++; state.validated = null; state.issues = [];
  updateStatus(); renderValidation(); renderHeading(); schedulePreview();
}
function transact(action) { snapshot(); action(); changed(); render(); }
function notify(text, error = false) {
  clearTimeout(noticeTimer); const area = $('notice'); area.replaceChildren(icon(error ? 'warning' : 'check'), el('span',text));
  area.className = `notice${error ? ' error' : ''}`; area.hidden = !text;
  if (!error) noticeTimer = setTimeout(() => { area.hidden = true; }, 4500);
}
async function api(path, data, workspace=state.activeProject) {
  const endpoint=path.startsWith('/api/')&&!path.startsWith('/api/projects')&&path!=='/api/definitions'?path+(path.includes('?')?'&':'?')+'workspace='+encodeURIComponent(workspace):path;
  const response = await fetch(endpoint, data === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  if(response.status===404&&(path==='/api/delete'||path==='/api/docker'||path.startsWith('/api/projects')))throw new Error('The running Build4Fun server is outdated. Restart the Python server to load the latest changes, then refresh this page.');
  const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Request failed.'); return result;
}
function guarded(fn) { return async event => { try { await fn(event); } catch (error) { notify(error.message,true); } }; }
function updateStatus() {
  const landing=state.view==='projects';
  document.querySelector('.toolbar-trailing').hidden=landing;
  document.querySelector('.statusbar').hidden=landing;
  $('save-status').textContent = state.saving ? 'Saving…' : dirty() ? 'Unsaved changes' : 'All changes saved';
  $('save').disabled = !state.ready || state.saving || state.deleting || !dirty(); $('undo').disabled = !state.history.length;
  const displayName=state.view==='projects'?'Projects':!state.activeProject?'No project selected':state.projects.find(p=>p.id===state.activeProject)?.name||projectName();
  $('sidebar-project').textContent = displayName; $('toolbar-project').textContent = displayName;
  const count = state.project?.children.filter(n => n.type === 'service').length || 0;
  $('workspace-count').textContent = `${count} service${count === 1 ? '' : 's'}`;
  $('validation-status').textContent = state.validated === true ? '✓ Configuration checked' : state.validated === false ? 'Configuration needs attention' : 'Not validated';
}
function references(kind) { return state.project.children.filter(n => definition(n).op === 'named' && definition(n).target === kind).map(n => n.values.name).filter(Boolean); }
function fieldError(field, value) {
  if(field.optional&&(value===undefined||value===null||value===''))return '';
  if (field.type === 'boolean') return typeof value === 'boolean' ? '' : 'Choose on or off.';
  if (!String(value ?? '').length && !field.allowEmpty) return `${field.label} is required.`;
  if (field.type === 'integer' && (!/^\d+$/.test(String(value)) || Number(value) < (field.min ?? 0) || Number(value) > (field.max ?? 65535))) return `${field.label} must be between ${field.min ?? 0} and ${field.max ?? 65535}.`;
  if(field.format==='ipv4'||field.format==='ipv4-network') {
    const parts=String(value).split('/'),ip=parts[0].split('.');
    const valid=ip.length===4&&ip.every(v=>/^(0|[1-9]\d{0,2})$/.test(v)&&Number(v)<=255);
    if(!valid||(field.format==='ipv4'&&parts.length!==1)||(field.format==='ipv4-network'&&(parts.length!==2||!/^\d+$/.test(parts[1])||Number(parts[1])>32)))return `Enter a valid ${field.format==='ipv4'?'IPv4 address':'IPv4 subnet in CIDR notation'}.`;
  }
  if (field.pattern && !new RegExp(`^(?:${field.pattern})$`).test(value)) return `Use a valid ${field.label.toLowerCase()}.`;
  if (field.type === 'choice' && !field.choices.includes(value)) return `Choose a ${field.label.toLowerCase()}.`;
  if (field.reference && !references(field.reference).includes(value)) return `Choose a declared ${field.label.toLowerCase()}.`;
  return '';
}
function collectIssues() {
  const issues = [];
  for (const node of nodes()) for (const field of definition(node).inputs || []) {
    const error = fieldError(field,node.values[field.key]); if (error) issues.push({id:node.id,key:field.key,message:error});
  }
  if (!state.project.children.some(n => n.type === 'project-name')) issues.push({id:state.project.id,message:'Add a project name.'});
  if (!state.project.children.some(n => n.type === 'service')) issues.push({id:state.project.id,message:'Add at least one service.'});
  for (const service of state.project.children.filter(n => n.type === 'service')) if (!service.children.some(n => n.type === 'image')) issues.push({id:service.id,message:'Add an image to this service.'});
  return issues;
}
function summarize(node) {
  const v = node.values;
  switch (node.type) {
    case 'image': return v.image || 'Choose an image';
    case 'port': return `${v.hostIp ? v.hostIp + ':' : ''}${v.published || '…'} → ${v.target || '…'} / ${v.protocol ? v.protocol.toUpperCase() : 'TCP (default)'}`;
    case 'variable': return `${v.key || 'Variable'} = ${v.value || '""'}`;
    case 'volume-mount': case 'bind-mount': return `${v.source || 'Source'} → ${v.target || 'Container path'}${v.readOnly ? ' · Read only' : ''}`;
    case 'network-attachment': return `${v.network || 'Choose a network'}${v.ipv4Address ? ' · ' + v.ipv4Address : ''}`;
    case 'external-network': return v.externalName ? `External · ${v.externalName}` : 'Existing Docker network';
    case 'named-volume': return 'Docker-managed storage';
    case 'network': return v.subnet ? `${v.subnet}${v.gateway ? ' · Gateway ' + v.gateway : ''}` : 'Compose-managed network';
    case 'ports': return node.children.length ? node.children.map(summarize).join(', ') : 'No port mappings';
    case 'environment': return `${node.children.length} variable${node.children.length === 1 ? '' : 's'}`;
    case 'mounts': return `${node.children.length} mount${node.children.length === 1 ? '' : 's'}`;
    case 'network-configuration': return node.children.length ? node.children.map(summarize).join(', ') : 'No network attachments';
    default: return node.children.length ? `${node.children.length} blocks` : Object.values(v).filter(v => typeof v === 'string' && v).join(' · ') || definition(node).help;
  }
}
/* Native dialogs provide focus trapping. Menus add arrow-key navigation. */
function closeMenu() { const d = $('menu-dialog'); if (d.open) d.close(); }
function openMenu(anchor, title, items, searchable = false) {
  closeMenu(); menuAnchor = anchor;
  const dialog = $('menu-dialog'); dialog.replaceChildren(el('div',title,'menu-title'));
  let search;
  if (searchable) { const holder = el('div',undefined,'menu-search'); search = el('input'); search.type='search'; search.placeholder='Find a block…'; search.setAttribute('aria-label','Find a block'); holder.append(search); dialog.append(holder); }
  const list = el('div',undefined,'menu-items'); list.setAttribute('role','menu'); dialog.append(list);
  const populate = () => {
    list.replaceChildren();
    const visible = items.filter(item => !search || item.label.toLowerCase().includes(search.value.toLowerCase()));
    visible.forEach(item => {
      const b = el('button',undefined,`menu-item${item.destructive ? ' destructive' : ''}`); b.type='button'; b.setAttribute('role','menuitem');
      b.append(icon(item.icon || 'plus'),el('span',item.label)); b.disabled=!!item.disabled;
      b.addEventListener('click',() => { closeMenu(); item.action(); });
      if (item.type) { b.draggable=true; b.addEventListener('dragstart',event => { state.drag={type:item.type}; event.dataTransfer.setData('text/plain',item.type); event.dataTransfer.effectAllowed='copy'; setTimeout(closeMenu,0); }); }
      list.append(b);
    });
    if (!visible.length) list.append(el('p','No matching actions.','menu-empty'));
  };
  if (search) search.addEventListener('input',populate); populate(); dialog.showModal();
  const rect = anchor.getBoundingClientRect();
  dialog.style.left = `${Math.max(8,Math.min(rect.left,innerWidth-dialog.offsetWidth-12))}px`;
  dialog.style.top = `${Math.max(8,Math.min(rect.bottom+6,innerHeight-dialog.offsetHeight-12))}px`;
  (search || list.querySelector('button:not(:disabled)'))?.focus();
}
$('menu-dialog').addEventListener('keydown',event => {
  if (!['ArrowDown','ArrowUp','Home','End'].includes(event.key)) return;
  event.preventDefault(); const items=[...$('menu-dialog').querySelectorAll('button:not(:disabled)')]; if (!items.length) return;
  const index=items.indexOf(document.activeElement);
  const next=event.key==='Home'?0:event.key==='End'?items.length-1:(index+(event.key==='ArrowDown'?1:-1)+items.length)%items.length;
  items[next].focus();
});
$('menu-dialog').addEventListener('click',event => { if(event.target===$('menu-dialog')) closeMenu(); });
$('menu-dialog').addEventListener('close',() => { if(menuAnchor?.isConnected) menuAnchor.focus({preventScroll:true}); });
function openForm(title, description, fill, submitLabel, onSubmit) {
  formAnchor=document.activeElement; const dialog=$('form-dialog'); dialog.replaceChildren();
  const form=el('form'); form.noValidate=true;
  const heading=el('div',undefined,'dialog-heading'); const h=el('h2',title); h.id='dialog-title'; heading.append(h,el('p',description));
  const fields=el('div',undefined,'dialog-fields'), error=el('p',undefined,'dialog-error'); error.setAttribute('role','alert');
  const actions=el('div',undefined,'dialog-actions'); const submit=button(submitLabel,()=>{},'primary'); submit.type='submit';
  actions.append(button('Cancel',()=>dialog.close(),'secondary'),submit); form.append(heading,fields,error,actions); dialog.append(form);
  const validate=fill(fields);
  form.addEventListener('submit',async event => { event.preventDefault(); error.textContent=''; if(validate && !validate()) return;
    submit.disabled=true; try { await onSubmit(); dialog.close(); } catch(e) { error.textContent=e.message; } finally { submit.disabled=false; }
  });
  dialog.showModal(); dialog.querySelector('input,select')?.focus();
}
$('form-dialog').addEventListener('close',()=>{if(formAnchor?.isConnected)formAnchor.focus({preventScroll:true});});
function addMenu(anchor,parent) {
  openMenu(anchor,`Add to ${nameOf(parent)}`,allowed(parent).map(type=>({label:state.definitions[type].label,icon:blockIcon(type),type,action:()=>createBlock(parent,type)})),true);
}
function createBlock(parent,type) {
  if(!allowed(parent).includes(type)) return;
  const node=makeBlock(type);
  if(type==='service') {
    const image=makeBlock('image'); node.children.push(image);
    openForm('Add service','Choose what this service is called and which image it uses.',holder=>{
      const checks=[...renderFields(holder,node,{draft:true}),...renderFields(holder,image,{draft:true})]; return ()=>checks.map(c=>c()).every(Boolean);
    },'Create service',()=>commitBlock(parent,node));
  } else if((definition(node).inputs || []).length) {
    openForm(`Add ${definition(node).label.toLowerCase()}`,definition(node).help,holder=>{
      const checks=renderFields(holder,node,{draft:true}); return ()=>checks.map(c=>c()).every(Boolean);
    },'Add block',()=>commitBlock(parent,node));
  } else {
    commitBlock(parent,node);
    const children=allowed(node); if(children.length===1) createBlock(node,children[0]);
  }
}
function commitBlock(parent,node) {
  state.arriving.add(node.id);
  transact(()=>{parent.children.push(node);state.selected=node.id;state.collapsed.delete(parent.id);state.view='build';});
  revealNode(node); notify(`${definition(node).label} added.`);
}
function revealNode(node) {
  let parent=parentOf(node),expanded=false; while(parent){if(state.collapsed.delete(parent.id))expanded=true;parent=parentOf(parent);}
  if(expanded&&state.view==='build')renderMain();
  requestAnimationFrame(()=>document.querySelector(`[data-node-id="${CSS.escape(node.id)}"]`)?.scrollIntoView({block:'nearest',behavior:'instant'}));
}
function selectNode(node,inspect=true) {
  state.selected=node.id;
  if(inspect){state.pane='inspector';renderDetail();}
  syncSelection(); highlightCode(); renderNavigation();
  if(inspect)requestAnimationFrame(()=>($('inspector-pane').querySelector('input,select')||$('inspector-pane').querySelector('button'))?.focus({preventScroll:true}));
}
function syncSelection() { document.querySelectorAll('[data-node-id]').forEach(e=>e.classList.toggle('is-selected',e.dataset.nodeId===state.selected)); }
function nodeMenu(anchor,node) {
  const parent=parentOf(node); if(!parent) return;
  const index=parent.children.indexOf(node);
  const items=[{label:'Edit',icon:'edit',action:()=>selectNode(node)},
    {label:'Move up',icon:'up',disabled:index===0,action:()=>moveSibling(node,-1)},
    {label:'Move down',icon:'down',disabled:index===parent.children.length-1,action:()=>moveSibling(node,1)}];
  if(!definition(node).single) items.push({label:'Duplicate',icon:'copy',action:()=>{
    const copy=JSON.parse(JSON.stringify(node)); nodes(copy).forEach(n=>{n.id=crypto.randomUUID();});
    if(definition(node).op==='named') { const key=definition(node).key; let base=(copy.values[key]||'untitled')+'-copy',name=base,i=2;
      while(parent.children.some(n=>definition(n).target===definition(node).target&&n.values[definition(n).key]===name))name=base+'-'+i++;
      copy.values[key]=name;
    }
    transact(()=>{parent.children.splice(index+1,0,copy);state.selected=copy.id;});notify('Block duplicated.');
  }});
  items.push({label:'Move to…',icon:'folder',action:()=>{
    const destinations=nodes().filter(n=>n!==parent&&!nodes(node).includes(n)&&allowed(n,node).includes(node.type));
    openMenu(anchor,'Move block',destinations.map(n=>({label:destinationName(n),icon:blockIcon(n.type),action:()=>moveNode(node,n)})),true);
  },disabled:!nodes().some(n=>n!==parent&&!nodes(node).includes(n)&&allowed(n,node).includes(node.type))});
  items.push({label:'Delete block',icon:'trash',destructive:true,action:()=>{
    transact(()=>{parent.children=parent.children.filter(n=>n!==node); if(nodes(node).some(n=>n.id===state.selected)){state.selected=null;state.pane=null;}});notify('Block deleted. Undo is available in the toolbar.');
  }});
  openMenu(anchor,nameOf(node),items);
}
function destinationName(node) { const parent=parentOf(node); return parent && parent.type!=='harness' ? `${nameOf(parent)} / ${nameOf(node)}` : nameOf(node); }
function moveSibling(node,offset) { const parent=parentOf(node),index=parent.children.indexOf(node);transact(()=>{[parent.children[index],parent.children[index+offset]]=[parent.children[index+offset],parent.children[index]];}); }
function moveNode(node,target) { const parent=parentOf(node); if(parent===target)return;transact(()=>{parent.children=parent.children.filter(n=>n!==node);target.children.push(node);state.collapsed.delete(target.id);});notify(`Moved to ${nameOf(target)}.`); }
function installDrag(handle,node) { handle.draggable=true;handle.classList.add('drag-handle');handle.title='Drag to another compatible container';handle.addEventListener('dragstart',event=>{state.drag={id:node.id,type:node.type};event.dataTransfer.setData('text/plain',node.type);event.dataTransfer.effectAllowed='move';}); }
function canDrop(parent) {
  const moving=state.drag?.id?find(state.drag.id):null;
  return !!(parent&&state.drag&&allowed(parent,moving).includes(state.drag.type)&&
    (!moving||(!nodes(moving).includes(parent)&&parentOf(moving)!==parent)));
}
function showDropTargets() {
  if(!state.drag)return;
  let count=0;
  document.querySelectorAll('[data-drop-parent]').forEach(element=>{
    const valid=canDrop(find(element.dataset.dropParent));
    element.classList.toggle('drop-eligible',valid);if(valid)count++;
  });
  const hint=$('drop-guidance');
  if(hint)hint.textContent=count?`Drop ${state.definitions[state.drag.type].label} into a highlighted destination.`:'No compatible destination. Add a suitable service or group first.';
}
function clearDropTargets() {
  state.drag=null;
  document.querySelectorAll('.drop-target,.drop-eligible').forEach(element=>element.classList.remove('drop-target','drop-eligible'));
  const hint=$('drop-guidance');if(hint)hint.textContent='Configuration belongs inside a service. Volumes and networks belong to the project.';
}
function installDrop(element,parent) {
  if(!(definition(parent).children||[]).length)return;
  element.dataset.dropParent=parent.id;
  element.dataset.dropLabel=parent===state.project?'Compose project':destinationName(parent);
  element.addEventListener('dragover',event=>{
    if(!canDrop(parent))return;event.preventDefault();event.stopPropagation();
    event.dataTransfer.dropEffect=state.drag.id?'move':'copy';
    document.querySelectorAll('.drop-target').forEach(e=>e.classList.remove('drop-target'));element.classList.add('drop-target');
    const hint=$('drop-guidance');if(hint)hint.textContent=`Release to ${state.drag.id?'move':'add'} ${state.definitions[state.drag.type].label} inside ${element.dataset.dropLabel}.`;
  });
  element.addEventListener('dragleave',event=>{if(!element.contains(event.relatedTarget)){element.classList.remove('drop-target');showDropTargets();}});
  element.addEventListener('drop',event=>{
    if(!canDrop(parent))return;event.preventDefault();event.stopPropagation();
    const drag=state.drag;clearDropTargets();
    if(drag.id)moveNode(find(drag.id),parent);else createBlock(parent,drag.type);
  });
}
/* Quiet rows expose detail only in the inspector. Input metadata stays definition-driven. */
function renderFields(holder,node,{draft=false}={}) {
  return (definition(node).inputs || []).map(field=>{
    if(node.values[field.key]===undefined)node.values[field.key]=field.type==='boolean'?false:'';
    const wrapper=el('div',undefined,'field'),label=el('label',field.label,'field-label');
    const id=`field-${node.id}-${field.key}`; label.htmlFor=id;
    let input;
    if(field.type==='choice'||field.reference){
      input=el('select'); input.append(new Option(field.placeholder||(field.optional?'Not set (optional)':'Choose…'),''));
      const options=field.reference?references(field.reference):field.choices;
      options.forEach(v=>input.append(new Option(v,v)));
      if(node.values[field.key]&&!options.includes(node.values[field.key]))input.append(new Option(`${node.values[field.key]} (missing)`,node.values[field.key]));
      input.value=node.values[field.key];
    }else{
      input=el('input');input.type=field.type==='boolean'?'checkbox':field.type==='integer'?'number':'text';
      if(field.type==='boolean')input.checked=node.values[field.key];else input.value=node.values[field.key];
      if(field.min!==undefined)input.min=field.min;if(field.max!==undefined)input.max=field.max;
      input.placeholder=field.label;input.autocomplete='off';input.spellcheck=false;
    }
    const labelRow=el('div',undefined,'field-label-row');labelRow.append(label);
    let help;
    if(field.help){
      help=el('div',field.help,'field-tooltip');help.id=id+'-help';help.setAttribute('role','tooltip');help.hidden=true;
      const info=iconButton('info',`About ${field.label}`,()=>showHelp(true));info.classList.add('field-info');
      info.setAttribute('aria-describedby',help.id);
      const showHelp=visible=>{help.hidden=!visible;};
      labelRow.append(info);
      info.addEventListener('mouseenter',()=>showHelp(true));
      wrapper.addEventListener('mouseleave',()=>{if(document.activeElement!==info)showHelp(false);});
      info.addEventListener('focus',()=>showHelp(true));
      info.addEventListener('blur',()=>showHelp(false));
      info.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();event.stopPropagation();showHelp(false);}});
      wrapper.append(help);
    }
    input.id=id; const error=el('span',undefined,'field-error');error.id=id+'-error';input.setAttribute('aria-describedby',error.id+(help?' '+help.id:''));
    const check=()=>{const text=fieldError(field,node.values[field.key]);error.textContent=text;input.setAttribute('aria-invalid',!!text);return !text;};
    if(field.type==='boolean'){wrapper.classList.add('checkbox-field');wrapper.append(labelRow,input,error);}else wrapper.append(labelRow,input,error);
    let editing=false;
    input.addEventListener('focus',()=>{editing=false;});
    input.addEventListener('input',()=>{
      if(!draft&&!editing){snapshot();editing=true;}
      node.values[field.key]=field.type==='boolean'?input.checked:input.value;
      if(!draft){changed();renderMain();renderNavigation();syncSelection();}
      if(state.touched.has(id))check();
    });
    input.addEventListener('blur',()=>{state.touched.add(id);check();});
    if(state.touched.has(id)||state.issues.some(i=>i.id===node.id&&i.key===field.key))check();
    if(field.file){
      const chooser=el('select');chooser.setAttribute('aria-label','Select project file or folder');chooser.append(new Option('Select from project…',''));
      state.files.forEach(f=>chooser.append(new Option(f.path+(f.directory?'/':''),f.path)));
      chooser.addEventListener('change',()=>{if(!chooser.value)return;if(!draft)snapshot();node.values[field.key]=chooser.value;input.value=chooser.value;if(!draft){changed();renderMain();}check();});wrapper.append(chooser);
      if(!draft)wrapper.append(button('Open file',guarded(()=>openFile(node.values[field.key])),'tertiary','file'));
    }
    if(field.reference&&!references(field.reference).length)wrapper.append(el('p','Declare this resource at project level first.','field-hint'));
    holder.append(wrapper);return check;
  });
}
function animateArrival(element,node) {
  if(state.arriving.delete(node.id))element.classList.add('arriving');
}
function configRow(node,{resource=false}={}) {
  const group=(definition(node).children||[]).length>0;
  const section=el('div',undefined,'config-section');animateArrival(section,node);installDrop(section,node);
  const row=el('div',undefined,`config-row${state.selected===node.id?' is-selected':''}`);row.dataset.nodeId=node.id;
  const select=el('button',undefined,'config-select');select.type='button';
  select.setAttribute('aria-label',`Inspect ${resource?nameOf(node):definition(node).label}`);
  const text=el('span',undefined,'config-text');text.append(el('strong',resource?nameOf(node):definition(node).label),el('span',summarize(node)));
  select.append(icon(blockIcon(node.type)),text);select.addEventListener('click',()=>selectNode(node,false));installDrag(select,node);row.append(select);
  const actions=el('div',undefined,'row-actions');
  if(group){
    const toggle=iconButton(state.collapsed.has(node.id)?'chevron':'down',`${state.collapsed.has(node.id)?'Expand':'Collapse'} ${definition(node).label}`,()=>{if(state.collapsed.has(node.id))state.collapsed.delete(node.id);else state.collapsed.add(node.id);renderMain();});
    toggle.setAttribute('aria-expanded',!state.collapsed.has(node.id));actions.append(toggle);
    actions.append(iconButton('plus',`Add to ${definition(node).label}`,event=>{const options=allowed(node);if(options.length===1)createBlock(node,options[0]);else addMenu(event.currentTarget,node);}));
  }else actions.append(iconButton('edit',`Edit ${definition(node).label}`,()=>selectNode(node)));
  actions.append(iconButton('more',`Actions for ${definition(node).label}`,event=>nodeMenu(event.currentTarget,node)));row.append(actions);section.append(row);
  if(group&&!state.collapsed.has(node.id)){
    const children=el('div',undefined,'config-children');
    if(!node.children.length)children.append(el('p','Nothing added yet. Use + to configure this section.','empty-inline'));
    node.children.forEach(child=>children.append(configRow(child)));section.append(children);
  }
  return section;
}
function serviceCard(node) {
  const card=el('article',undefined,'service-card');animateArrival(card,node);card.dataset.nodeId=node.id;installDrop(card,node);
  const header=el('div',undefined,'service-header'),symbol=el('span',undefined,'service-icon');symbol.append(icon('cube'));installDrag(symbol,node);
  const title=el('button',undefined,'service-title');title.type='button';title.append(el('strong',node.values.name||'Unnamed service'),el('span','Service'));title.addEventListener('click',()=>selectNode(node,false));
  const meta=el('div',undefined,'service-meta');const status=el('span',undefined,`status${state.validated===true?' valid':state.issues.some(i=>nodes(node).some(n=>n.id===i.id))?' warning':''}`);
  status.append(icon(state.validated===true?'check':'cube'),el('span',state.validated===true?'Checked':state.issues.some(i=>nodes(node).some(n=>n.id===i.id))?'Needs attention':'Draft'));
  const collapse=iconButton(state.collapsed.has(node.id)?'chevron':'down',`${state.collapsed.has(node.id)?'Expand':'Collapse'} ${node.values.name||'service'}`,()=>{if(state.collapsed.has(node.id))state.collapsed.delete(node.id);else state.collapsed.add(node.id);renderMain();});collapse.setAttribute('aria-expanded',!state.collapsed.has(node.id));
  meta.append(status,collapse,iconButton('more',`Actions for ${node.values.name||'service'}`,event=>nodeMenu(event.currentTarget,node)));header.append(symbol,title,meta);card.append(header);
  if(!state.collapsed.has(node.id)){
    const configuration=el('div',undefined,'service-configuration');configuration.setAttribute('role','group');configuration.setAttribute('aria-label',`Configuration for ${node.values.name||'service'}`);
    node.children.forEach(child=>configuration.append(configRow(child)));card.append(configuration);
    const footer=el('div',undefined,'card-footer');const add=button('Add configuration',event=>addMenu(event.currentTarget,node),'tertiary','plus');add.disabled=!allowed(node).length;footer.append(add);card.append(footer);
  }
  return card;
}
function sectionHeading(title,count,action) {const h=el('div',undefined,'section-heading'),label=el('h2',title);if(count!==undefined)label.append(el('span',String(count),'section-count'));h.append(label);if(action)h.append(action);return h;}
function emptyState(title,description,action,glyph='cube') {const area=el('div',undefined,'empty-state'),symbol=el('div',undefined,'empty-symbol');symbol.append(icon(glyph));area.append(symbol,el('h2',title),el('p',description));if(action)area.append(action);return area;}
function renderBuilder(content) {
  const project=state.project,name=project.children.find(n=>n.type==='project-name');
  const strip=el('div',undefined,'project-strip');strip.append(icon('build'),button('Compose project',()=>{state.pane=null;selectNode(project,false);renderDetail();},'tertiary'),el('strong',projectName()));
  strip.append(button(name?'Edit name':'Set project name',()=>name?selectNode(name):createBlock(project,'project-name'),'tertiary', 'edit'));content.append(strip);
  const hint=el('p','Configuration belongs inside a service. Volumes and networks belong to the project.','drop-guidance');hint.id='drop-guidance';hint.setAttribute('role','status');content.append(hint);
  const services=project.children.filter(n=>n.type==='service');
  content.append(sectionHeading('Services',services.length,services.length?button('Add service',()=>createBlock(project,'service'),'tertiary','plus'):null));
  const serviceList=el('div');
  if(!services.length)serviceList.append(emptyState('No services yet','Services are the containers that make up your environment. Start with a name and an image.',button('Add service',()=>createBlock(project,'service'),'primary','plus')));
  services.forEach(node=>serviceList.append(serviceCard(node)));content.append(serviceList);
  const projectNetworks=project.children.filter(n=>n.type==='network');
  const networksSection=el('section',undefined,'resource-section');
  networksSection.append(sectionHeading('Project networks',projectNetworks.length,button('Add network',()=>createBlock(project,'network'),'tertiary','plus')));
  if(projectNetworks.length){const list=el('div',undefined,'resource-list');projectNetworks.forEach(n=>list.append(configRow(n,{resource:true})));networksSection.append(list);}
  else networksSection.append(el('p','Define networks and subnets that Compose creates for this project.','empty-inline'));
  content.append(networksSection);
  const resources=project.children.filter(n=>!['service','project-name','network'].includes(n.type));
  const section=el('section',undefined,'resource-section');
  section.append(sectionHeading('Shared resources',resources.length,button('Add resource',event=>{
    const choices=allowed(project).filter(t=>!['service','project-name','network'].includes(t));openMenu(event.currentTarget,'Add shared resource',choices.map(type=>({label:state.definitions[type].label,icon:blockIcon(type),type,action:()=>createBlock(project,type)})),true);
  },'tertiary','plus')));
  if(resources.length){const list=el('div',undefined,'resource-list');resources.forEach(n=>list.append(configRow(n,{resource:true})));section.append(list);}
  else section.append(el('p','Declare named volumes or reference existing external networks here.','empty-inline'));
  content.append(section);installDrop(content,project);
}
function blockPalette() {
  const palette=el('section',undefined,'block-palette');palette.setAttribute('aria-label','Block palette');
  palette.append(el('p','ADD BLOCKS','nav-label'));
  let parent=find(state.selected)||state.project;
  while(parent&&!(definition(parent).children||[]).length)parent=parentOf(parent);
  parent=parent||state.project;
  palette.append(el('p',parent===state.project?'Project-level blocks':`For ${destinationName(parent)}`,'palette-context'));
  const list=el('div',undefined,'palette-blocks');palette.append(list);
  const populate=()=>{
    list.replaceChildren();
    const options=allowed(parent);
    for(const type of options){
      const d=state.definitions[type];
      const add=button(d.label,()=>createBlock(parent,type),'secondary',blockIcon(type));
      add.setAttribute('aria-label',`Add ${d.label} to ${parent===state.project?'Compose project':nameOf(parent)}`);
      add.title=d.help||d.label;add.draggable=true;
      add.addEventListener('dragstart',event=>{state.drag={type};event.dataTransfer.setData('text/plain',type);event.dataTransfer.effectAllowed='copy';});
      list.append(add);
    }
    if(!options.length)list.append(el('p','All available blocks are already added here.','empty-inline'));
  };
  populate();
  palette.append(el('p','Click to add here, or drag into a compatible block.','palette-hint'));
  return palette;
}
function renderNavigation() {
  const nav=$('workspace-navigation');nav.replaceChildren(el('p','WORKSPACE','nav-label'));
  const projectRow=el('div',undefined,'projects-navigation');
  const projects=button('Projects',()=>{state.projectsExpanded=!state.projectsExpanded;renderNavigation();$('projects-toggle').focus();},'tertiary',state.projectsExpanded?'down':'chevron');projects.id='projects-toggle';projects.className='nav-row';projects.setAttribute('aria-expanded',String(state.projectsExpanded));projects.setAttribute('aria-controls','project-tree');
  projectRow.append(projects,iconButton('more','Manage projects',()=>navigate('projects')));
  if(state.view!=='projects')projectRow.append(iconButton('plus','New project',newProject));
  nav.append(projectRow);
  const tree=el('div',undefined,'project-tree');tree.id='project-tree';tree.hidden=!state.projectsExpanded;
  for(const project of state.projects){
    const entry=button(project.name,guarded(async()=>{
      await switchProject(project.id);state.selected=null;state.pane=null;navigate('build');
    }),'tertiary','build');entry.className='nav-row project-tree-entry';entry.title=project.name;
    entry.setAttribute('aria-current',project.id===state.activeProject?'page':'false');tree.append(entry);
  }
  if(!state.projects.length)tree.append(el('p','No projects yet.','empty-inline'));
  nav.append(tree);
  if(state.activeProject){
    const fileHeader=el('div',undefined,'files-navigation');
    const toggle=button('Files',()=>{state.filesExpanded=!state.filesExpanded;renderNavigation();$('files-toggle').focus();},'tertiary',state.filesExpanded?'down':'chevron');
    toggle.id='files-toggle';toggle.className='nav-row';toggle.setAttribute('aria-label','Files');toggle.setAttribute('aria-expanded',String(state.filesExpanded));toggle.setAttribute('aria-controls','project-files');
    toggle.append(el('span',String(state.files.filter(file=>!file.directory).length),'count'));
    fileHeader.append(toggle,iconButton('plus','Create file or folder',event=>fileMenu(event.currentTarget)));nav.append(fileHeader);
    const explorer=el('div',undefined,'project-files');explorer.id='project-files';explorer.hidden=!state.filesExpanded;
    const projectLabel=state.projects.find(project=>project.id===state.activeProject)?.name||projectName();
    explorer.setAttribute('aria-label',`Files for ${projectLabel}`);
    explorer.append(el('p',projectLabel,'explorer-project-name'),renderFileTree());
    if(!state.files.length)explorer.append(el('p','No files yet. Use + to add a file or folder.','empty-inline'));
    nav.append(explorer);
  }
  const side=$('sidebar-content');side.replaceChildren();
  if(state.view==='projects')side.append(el('p','Each project keeps its own blocks and files.','project-sidebar-note'));
  else if(state.view==='build')side.append(blockPalette());
  updateStatus();
}
function renderHeading() {
  const titles={runtime:['PROJECT','Environment'],projects:['WORKSPACE','Projects'],build:['WORKSPACE','Build environment'],compose:['WORKSPACE','Build environment'],files:['PROJECT','Project files'],file:['PROJECT FILE',state.file.split('/').pop()]};
  $('page-eyebrow').textContent=titles[state.view][0];$('page-title').textContent=titles[state.view][1];const actions=$('page-actions');actions.replaceChildren();
  if(state.view==='build'||state.view==='compose'){
    if(state.validated===true){const badge=el('span',undefined,'validation-badge');badge.append(icon('check'),el('span','Checked'));actions.append(badge);}
    if(state.activeProject==='legacy'&&!state.project.children.length&&!state.dirty)actions.append(button('Open saved project',guarded(openSavedProject),'secondary','folder'));
    actions.append(button('Validate',guarded(validateProject),'secondary','check'));
    actions.append(button('Environment',()=>navigate('runtime'),'secondary','cube'));
    if(state.view==='build'){
      const toggle=button(state.previewVisible?'Hide YAML':'Show YAML',()=>{
        state.previewVisible=!state.previewVisible;renderHeading();renderDetail();
      },'secondary','code');toggle.classList.add('desktop-preview-toggle');toggle.setAttribute('aria-pressed',String(state.previewVisible));actions.append(toggle);
      const yaml=button('YAML',()=>navigate('compose'),'secondary','code');yaml.classList.add('mobile-preview-toggle');actions.append(yaml);
    }else actions.append(button('Blocks',()=>navigate('build'),'secondary','build'));
  }else if(state.view==='projects')actions.append(button('New project',newProject,'primary','plus'));
  else if(state.view==='runtime')actions.append(button('Back to build',()=>navigate('build'),'secondary','build'));
  else if(state.view==='files')actions.append(button('New file',()=>createFile(false),'primary','plus'));
  else { actions.append(button('Back to build',()=>navigate('build'),'secondary','build')); actions.append(button('Show in explorer',()=>{state.filesExpanded=true;renderNavigation();if(innerWidth<=720)$('app').classList.add('mobile-nav');},'secondary','folder')); }
}
function renderMain() {
  const content=$('content');content.replaceChildren();
  if(state.view==='runtime')renderRuntime(content);
  else if(state.view==='projects')renderProjects(content);
  else if(state.view==='build')renderBuilder(content);
  else if(state.view==='compose')content.append(composePane(false));
  else if(state.view==='file')renderEditor(content);
  else{
    if(!state.files.length)content.append(emptyState('A place for your configuration','Create the files your services need, then attach them with a Bind mount block.',button('New file',()=>createFile(false),'primary','plus'),'folder'));
    else{const list=el('div',undefined,'resource-list');list.append(renderFileTree(true));content.append(list);}
  }
  syncSelection();
}
function renderDetail() {
  const preview=$('detail-pane'),pane=$('inspector-pane'),grid=$('workspace-grid');
  const visible=(state.view==='build'&&state.previewVisible)||state.view==='file';
  preview.hidden=!visible;
  if(!visible)preview.replaceChildren();
  grid.className=`workspace-grid${visible?' persistent-preview':''}`;
  $('workspace').classList.toggle('builder-workspace',visible);
  preview.className='detail-pane compose-pane';
  if(visible&&!preview.firstChild)preview.append(composePane(true));
  const node=find(state.selected);
  const inspecting=state.view==='build'&&state.pane==='inspector'&&node;
  pane.hidden=!inspecting;pane.replaceChildren();
  if(!inspecting)return;
  const header=el('div',undefined,'pane-header');
  header.append(el('strong','Inspector'),iconButton('close','Close inspector',()=>{
    state.pane=null;renderDetail();
    document.querySelector(`[data-node-id="${CSS.escape(node.id)}"] button`)?.focus({preventScroll:true});
  }));pane.append(header);
  const body=el('div',undefined,'inspector-content');
  body.append(el('p',definition(node).label.toUpperCase(),'eyebrow'),el('h2',nameOf(node)),el('p',definition(node).help,'inspector-help'));
  renderFields(body,node);
  if((definition(node).children||[]).length){
    node.children.forEach(child=>body.append(button(definition(child).label,()=>selectNode(child),'secondary',blockIcon(child.type))));
    const add=button('Add configuration',event=>addMenu(event.currentTarget,node),'tertiary','plus');add.disabled=!allowed(node).length;body.append(add);
  }
  state.issues.filter(i=>i.id===node.id&&!i.key).forEach(e=>body.append(el('p',e.message,'field-error')));
  pane.append(body);
}
function renderValidation() {
  const area=$('validation-summary');area.replaceChildren();area.hidden=!state.issues.length;area.className='validation-summary';
  if(!state.issues.length)return;
  area.append(el('strong',`${state.issues.length} thing${state.issues.length===1?'':'s'} to check`));
  state.issues.forEach(issue=>{const node=find(issue.id);const b=el('button',`${node?nameOf(node)+': ':''}${issue.message}`);b.type='button';b.addEventListener('click',()=>{state.view='build';render();if(node?.type==='harness'&&!state.project.children.some(n=>n.type==='project-name'))createBlock(state.project,'project-name');else if(node){selectNode(node);revealNode(node);}});area.append(b);});
}
function render() {if(!state.ready)return;renderNavigation();renderHeading();renderMain();renderDetail();renderValidation();updateStatus();schedulePreview();}
function navigate(view) {state.view=view;state.pane=view==='build'?state.pane:null;$('app').classList.remove('mobile-nav');render();$('workspace').scrollTop=0;}
/* File editing deliberately has no service-configuration diagnostics. */
function fileMenu(anchor) {openMenu(anchor,'Create in project',[{label:'New file',icon:'file',action:()=>createFile(false)},{label:'New folder',icon:'folder',action:()=>createFile(true)}]);}
function renderFileTree(full=false) {
  const root={children:new Map()};
  for(const file of state.files){let cursor=root;const parts=file.path.split('/');parts.forEach((part,index)=>{if(!cursor.children.has(part))cursor.children.set(part,{name:part,path:parts.slice(0,index+1).join('/'),directory:index<parts.length-1||file.directory,children:new Map()});cursor=cursor.children.get(part);});}
  const walk=branch=>{const list=el('ul',undefined,'file-tree');
    [...branch.children.values()].sort((a,b)=>Number(b.directory)-Number(a.directory)||a.name.localeCompare(b.name)).forEach(entry=>{
      const item=el('li'),row=el('button',undefined,`file-row${state.file===entry.path&&state.view==='file'?' active':''}`);row.type='button';row.setAttribute('aria-label',entry.name);
      row.append(icon(entry.directory?(state.folders.has(entry.path)?'chevron':'down'):'file'),el('span',entry.name));
      if(entry.directory){row.setAttribute('aria-expanded',!state.folders.has(entry.path));row.addEventListener('click',()=>{if(state.folders.has(entry.path))state.folders.delete(entry.path);else state.folders.add(entry.path);renderNavigation();if(full)renderMain();});}
      else{row.addEventListener('click',guarded(()=>openFile(entry.path)));if(state.drafts.get(entry.path)?.dirty){row.setAttribute('aria-description','Unsaved changes');const dot=el('span','•','file-draft');dot.setAttribute('aria-label','Unsaved changes');row.append(dot);}}
      const wrapper=el('div',undefined,'explorer-entry');
      const actions=iconButton('more',`File actions for ${entry.path}`,()=>fileActions(actions,entry));
      wrapper.append(row,actions);
      wrapper.addEventListener('contextmenu',event=>{event.preventDefault();fileActions(row,entry);});
      row.addEventListener('keydown',event=>{
        if(event.key==='Delete'||(event.metaKey&&event.key==='Backspace')){event.preventDefault();deleteFile(entry);}
        else if(event.key==='ContextMenu'||(event.shiftKey&&event.key==='F10')){event.preventDefault();fileActions(row,entry);}
      });
      item.append(wrapper);if(entry.directory&&!state.folders.has(entry.path))item.append(walk(entry));list.append(item);
    });return list;
  };return walk(root);
}
function fileActions(anchor,entry) {
  const items=entry.directory?[
    {label:'New file',icon:'file',action:()=>createFile(false,entry.path)},
    {label:'New folder',icon:'folder',action:()=>createFile(true,entry.path)}
  ]:[{label:'Open',icon:'file',action:guarded(()=>openFile(entry.path))}];
  items.push({label:'Delete',icon:'trash',destructive:true,disabled:state.saving||state.deleting,action:()=>deleteFile(entry)});
  openMenu(anchor,entry.name,items);
}
function deleteFile(entry) {
  if(state.saving||state.deleting){notify('Wait for the current file operation to finish.',true);return;}
  const inside=path=>path===entry.path||(entry.directory&&path.startsWith(entry.path+'/'));
  const unsaved=[...state.drafts].filter(([path,draft])=>inside(path)&&draft.dirty).length;
  const affected=nodes().filter(node=>{
    if(node.type!=='bind-mount')return false;
    const source=String(node.values.source||'').split('/').filter(part=>part&&part!=='.').join('/');
    return source&&(inside(source)||entry.path.startsWith(source+'/'));
  });
  openForm(`Delete ${entry.directory?'folder':'file'}?`,
    `“${entry.path}”${entry.directory?' and all of its contents':''} will be permanently deleted. This cannot be undone.`,holder=>{
      if(unsaved)holder.append(el('p',`${unsaved} file${unsaved===1?' has':'s have'} unsaved changes that will be discarded.`,'field-hint'));
      if(affected.length)holder.append(el('p',`${affected.length} bind mount${affected.length===1?' references':'s reference'} this path or its contents. Those blocks will remain and must be updated manually.`,'field-hint'));
    },'Delete permanently',async()=>{
      if(state.saving)throw new Error('Wait for saving to finish.');
      state.deleting=true;++fileRequest;updateStatus();
      try {
        await api('/api/delete',{path:entry.path});
        for(const path of state.drafts.keys())if(inside(path))state.drafts.delete(path);
        for(const path of state.folders)if(inside(path))state.folders.delete(path);
        state.files=state.files.filter(file=>!inside(file.path));
        if(inside(state.file)){state.file='';state.view='build';state.pane=null;}
        render();notify(`${entry.directory?'Folder':'File'} deleted.`);
      } finally {state.deleting=false;updateStatus();}
    });
  $('form-dialog').querySelector('[type="submit"]').className='button danger';
  $('form-dialog').querySelector('.dialog-actions button').focus();
}
function createFile(folder,parentPath='') {
  let input;
  openForm(folder?'New folder':'New file','Use a path relative to this project, such as config/dnsmasq.conf.',holder=>{
    const field=el('div',undefined,'field'),label=el('label','Project path','field-label');label.htmlFor='new-path';input=el('input');input.id='new-path';input.value=parentPath?parentPath+'/':'';input.placeholder=folder?'config':'config/dnsmasq.conf';field.append(label,input);holder.append(field);
    return ()=>{if(!input.value.trim()){input.setCustomValidity('Enter a path.');input.reportValidity();return false;}input.setCustomValidity('');return true;};
  },'Create',async()=>{
    const path=input.value.trim();await api(folder?'/api/folder':'/api/file',folder?{path}:{path,content:'',create:true});state.files=await api('/api/files');
    state.filesExpanded=true;
    const parts=path.split('/');for(let i=1;i<=parts.length;i++)state.folders.delete(parts.slice(0,i).join('/'));
    if(folder){render();}else await openFile(path);notify(folder?'Folder created.':'File created.');
  });
}
async function openFile(path) {
  if(state.deleting)return;
  const request=++fileRequest;
  if(!path)throw new Error('Choose a project file first.');
  if(!state.drafts.has(path)){const result=await api(`/api/file?path=${encodeURIComponent(path)}`);if(request!==fileRequest)return;state.drafts.set(path,{content:result.content,dirty:false,revision:0,caret:0,scroll:0});}
  state.file=path;state.view='file';state.pane=null;state.filesExpanded=true;
  const parts=path.split('/');for(let i=1;i<parts.length;i++)state.folders.delete(parts.slice(0,i).join('/'));
  $('app').classList.remove('mobile-nav');render();
}
function renderEditor(content) {
  const draft=state.drafts.get(state.file),shell=el('div',undefined,'file-editor-shell'),header=el('div',undefined,'pane-header');
  const label=el('div');label.append(icon('file'),el('strong',state.file));header.append(label,el('span','Plain text','save-status'));
  const body=el('div',undefined,'editor-body'),numbers=el('pre',undefined,'editor-lines');numbers.setAttribute('aria-hidden','true');
  const editor=el('textarea');editor.value=draft.content;editor.spellcheck=false;editor.wrap='off';editor.setAttribute('aria-label',`Edit ${state.file}`);
  const lineNumbers=()=>{numbers.textContent=Array.from({length:editor.value.split('\n').length},(_,i)=>i+1).join('\n');};lineNumbers();
  editor.addEventListener('input',()=>{draft.content=editor.value;draft.dirty=true;draft.revision++;lineNumbers();updateStatus();renderNavigation();});
  const remember=()=>{draft.caret=editor.selectionStart;draft.scroll=editor.scrollTop;numbers.scrollTop=editor.scrollTop;};
  ['keyup','click','scroll','blur'].forEach(event=>editor.addEventListener(event,remember));
  editor.addEventListener('keydown',event=>{if(event.key==='Tab'){event.preventDefault();const start=editor.selectionStart,end=editor.selectionEnd;editor.setRangeText('  ',start,end,'end');editor.dispatchEvent(new Event('input'));}});
  body.append(numbers,editor);shell.append(header,body,el('p','Configuration contents are yours to research and troubleshoot. Files are not validated.','code-hint'));content.append(shell);
  editor.setSelectionRange(draft.caret,draft.caret);editor.scrollTop=draft.scroll;numbers.scrollTop=draft.scroll;
}
async function saveAll() {
  if(!state.activeProject||state.saving||state.deleting)return;state.saving=true;updateStatus();
  try{
    if(state.dirty){const revision=state.revision;await api('/api/project',{project:state.project});if(state.revision===revision)state.dirty=false;}
    for(const [path,draft] of state.drafts){if(!draft.dirty)continue;const revision=draft.revision;await api('/api/file',{path,content:draft.content});if(draft.revision===revision)draft.dirty=false;}
    state.projects=await api('/api/projects');notify(dirty()?'Saved. Newer edits are still unsaved.':'All changes saved.');renderNavigation();if(state.view==='projects')renderMain();
  }finally{state.saving=false;updateStatus();if(state.view==='projects')renderMain();}
}
function renderRuntime(content) {
  content.append(el('p','Start saves this project and its edited files before applying the configuration. Stop preserves containers and data. Logs are shown as reported by the services.','runtime-intro'));
  const actions=el('div',undefined,'runtime-actions');
  for(const [action,label] of [['validate','Check with Docker'],['start','Start / Apply'],['stop','Stop'],['status','Refresh status'],['logs','View logs']]){
    const control=button(label,guarded(()=>runDocker(action)),action==='start'?'primary':'secondary');control.disabled=state.runtimeBusy;actions.append(control);
  }
  const remove=button('Remove deployment',()=>openForm('Remove deployment?','Remove this project’s containers and Compose-managed networks. Named volumes, external networks, and project files will remain.',()=>{},'Remove deployment',()=>runDocker('remove')),'tertiary','trash');remove.disabled=state.runtimeBusy;actions.append(remove);content.append(actions);
  if(state.runtimeBusy)content.append(el('p','Working with Docker… Image downloads can take a few minutes.','save-status'));
  if(state.runtimeServices.length){
    const table=el('table',undefined,'runtime-status');table.setAttribute('aria-label','Service status');
    const header=el('tr');['Service','Container','State','Health','Exit code'].forEach(label=>header.append(el('th',label)));const head=el('thead');head.append(header);table.append(head);
    const body=el('tbody');state.runtimeServices.forEach(service=>{const row=el('tr');[service.Service,service.Name,service.State,service.Health||'—',service.ExitCode??'—'].forEach(value=>row.append(el('td',String(value??''))));body.append(row);});table.append(body);const scroll=el('div',undefined,'runtime-table-scroll');scroll.append(table);content.append(scroll);
  }
  const output=el('pre',state.runtimeOutput||'Choose an action to check Docker, view service status, or read logs.','runtime-output');output.setAttribute('aria-label','Docker output');output.setAttribute('role','status');content.append(output);
}
async function runDocker(action) {
  if(state.runtimeBusy||state.saving||state.deleting)return;
  if(action==='start')await saveAll();
  state.runtimeBusy=true;state.runtimeServices=[];renderMain();
  try {
    const result=await api('/api/docker',{action,...(action==='validate'?{project:state.project}:{})});
    state.runtimeServices=result.services||[];
    state.runtimeOutput=result.output||result.message||(result.deployed?'No containers found for this deployment.':'This project has not been deployed.');
    if(action==='status'&&result.services?.length)state.runtimeOutput='Status refreshed from Docker.';
  }catch(error){state.runtimeOutput=error.message;}
  finally{state.runtimeBusy=false;if(state.view==='runtime')renderMain();}
}
/* Compose is generated on the server. Its source map links lines back to blocks. */
function composePane(compact) {
  const shell=el('div',undefined,'code-shell');const header=el('div',undefined,'pane-header'),title=el('div');title.append(icon('code'),el('strong','compose.yaml'));
  const actions=el('div');actions.append(iconButton('download','Download compose.yaml',()=>downloadCompose()));
  if(compact)actions.append(iconButton('code','Open full Compose preview',()=>navigate('compose')));header.append(title,actions);
  const output=el('div',undefined,'preview-output');shell.append(header,output,el('p','Select a YAML line to find its block. Generated output is read-only.','code-hint'));
  paintPreview(output);return shell;
}
function schedulePreview() {
  clearTimeout(previewTimer);if(!['build','file','compose'].includes(state.view))return;
  previewTimer=setTimeout(()=>refreshPreview(),180);
}
async function refreshPreview() {
  if(state.previewRevision===state.revision){paintAllPreviews();return;}
  const request=++previewRequest,revision=state.revision;
  try{const result=await api('/api/preview',{project:state.project});if(request!==previewRequest||revision!==state.revision)return;state.preview=result;state.previewError='';state.previewRevision=revision;}
  catch(error){if(request!==previewRequest||revision!==state.revision)return;state.preview=null;state.previewError=error.message;state.previewRevision=revision;}
  paintAllPreviews();
}
function paintAllPreviews(){document.querySelectorAll('.preview-output').forEach(paintPreview);}
function paintPreview(output) {
  output.replaceChildren();
  if(state.previewRevision!==state.revision){output.append(el('p','Generating preview…','code-empty'));return;}
  if(!state.preview){output.append(el('p','Complete the required configuration to generate Compose YAML. Use Validate to locate missing or invalid settings.','code-empty'));return;}
  const code=el('div',undefined,'code-body');code.setAttribute('aria-label','Generated Compose YAML');code.tabIndex=0;
  const ranges=Object.entries(state.preview.blocks||{}).sort((a,b)=>(a[1].end-a[1].start)-(b[1].end-b[1].start));
  state.preview.yaml.trimEnd().split('\n').forEach((line,index)=>{
    const origin=ranges.find(([,range])=>index+1>=range.start&&index+1<=range.end);
    const row=el(origin?'button':'div',undefined,'code-line');if(origin){row.type='button';row.dataset.blockId=origin[0];row.setAttribute('aria-label',`Line ${index+1}: ${line.trim()}`);row.addEventListener('click',()=>{const node=find(origin[0]);if(!node)return;if(state.view==='compose'){state.view='build';state.pane=null;state.selected=node.id;render();}else selectNode(node,false);revealNode(node);});}
    const number=el('span',String(index+1),'line-number');number.setAttribute('aria-hidden','true');row.append(number);
    const match=line.match(/^(\s*(?:- )?[^:#]+:)(.*)$/);if(match)row.append(el('span',match[1],'yaml-key'),el('span',match[2],'yaml-value'));else row.append(el('span',line));code.append(row);
  });output.append(code);highlightCode();
}
function highlightCode(){const range=state.preview?.blocks?.[state.selected];document.querySelectorAll('.code-body').forEach(code=>[...code.children].forEach((row,index)=>row.classList.toggle('highlight',!!range&&index+1>=range.start&&index+1<=range.end)));}
function downloadCompose(){if(!state.preview||state.previewRevision!==state.revision){notify('Generate a valid Compose preview before downloading.',true);return;}const url=URL.createObjectURL(new Blob([state.preview.yaml],{type:'application/yaml'})),link=el('a');link.href=url;link.download='compose.yaml';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function validateProject() {
  const revision=state.revision;state.issues=collectIssues();
  if(!state.issues.length){
    try{const result=await api('/api/preview',{project:state.project});if(state.revision!==revision)return;state.preview=result;state.previewRevision=revision;state.previewError='';}
    catch(error){if(state.revision!==revision)return;const id=error.message.match(/\[([^\]]+)\]/)?.[1];const serviceName=error.message.match(/^Service ([^:]+):/)?.[1];const service=state.project.children.find(n=>n.type==='service'&&n.values.name===serviceName);state.issues=[{id:id||service?.id||state.project.id,message:error.message}];}
  }
  state.validated=!state.issues.length;render();
  if(state.validated)notify('Block and assembly checks passed. Use Check with Docker in Environment for Docker Compose validation.');
  else{const first=state.issues[0];if(first.id!==state.project.id){state.view='build';state.selected=first.id;state.pane='inspector';render();revealNode(find(first.id));}}
}
function undo(){if(!state.history.length)return;state.project=JSON.parse(state.history.pop());if(!find(state.selected)){state.selected=null;state.pane=null;}changed();render();notify('Last project change undone.');}
function setTheme(mode){localStorage.setItem('build4fun-theme',mode);const dark=mode==='dark'||(mode==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=dark?'dark':'light';}
$('theme').append(icon('theme'));$('theme').onclick=event=>openMenu(event.currentTarget,'Appearance',['system','light','dark'].map(mode=>({label:mode[0].toUpperCase()+mode.slice(1),icon:'theme',action:()=>setTheme(mode)})));
setTheme(localStorage.getItem('build4fun-theme')||'system');matchMedia('(prefers-color-scheme: dark)').addEventListener('change',()=>{if((localStorage.getItem('build4fun-theme')||'system')==='system')setTheme('system');});
$('toggle-sidebar').append(icon('sidebar'));$('toggle-sidebar').onclick=()=>{const app=$('app'),mobile=innerWidth<=720;app.classList.toggle(mobile?'mobile-nav':'nav-collapsed');$('toggle-sidebar').setAttribute('aria-expanded',mobile?app.classList.contains('mobile-nav'):!app.classList.contains('nav-collapsed'));};
$('undo').append(icon('undo'));$('undo').onclick=undo;$('save').onclick=guarded(saveAll);
window.addEventListener('beforeunload',event=>{if(dirty()||[...projectSessions].some(([id,s])=>id!==state.activeProject&&(s.dirty||[...s.drafts.values()].some(d=>d.dirty)))){event.preventDefault();event.returnValue='';}});
document.addEventListener('dragstart',()=>{requestAnimationFrame(showDropTargets);});
document.addEventListener('dragend',clearDropTargets);
document.addEventListener('drop',clearDropTargets);
document.addEventListener('keydown',event=>{
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();if(state.ready)guarded(saveAll)();}
  if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'&&!event.target.closest('input,textarea,select')&&!$('form-dialog').open){event.preventDefault();undo();}
  if(event.key==='Escape'&&!$('form-dialog').open&&!$('menu-dialog').open&&state.pane==='inspector'){state.pane=null;renderDetail();}
});
const sessionKeys=['project','files','view','pane','selected','dirty','history','drafts','file','filesExpanded','collapsed','folders','touched','issues','validated','arriving'];
async function switchProject(identity) {
  if(identity===state.activeProject||state.switching)return;
  if(state.saving||state.deleting||state.runtimeBusy)throw new Error('Wait for the current file operation to finish.');
  state.switching=true;$('app').inert=true;++fileRequest;++previewRequest;clearTimeout(previewTimer);
  try {
    let session=projectSessions.get(identity);
    if(!session){
      // Explicit URLs keep these reads bound to their destination project.
      const read=async path=>{const response=await fetch(path+'?workspace='+encodeURIComponent(identity));const result=await response.json();if(!response.ok)throw new Error(result.error);return result;};
      const [project,files]=await Promise.all([read('/api/project'),read('/api/files')]);
      session={project,files,view:'build',pane:null,selected:null,dirty:false,history:[],drafts:new Map(),file:'',filesExpanded:true,collapsed:new Set(nodes(project).filter(node=>definition(node).op==='group').map(node=>node.id)),folders:new Set(),touched:new Set(),issues:[],validated:null,arriving:new Set()};
    }
    if(state.activeProject)projectSessions.set(state.activeProject,Object.fromEntries(sessionKeys.map(key=>[key,state[key]])));
    Object.assign(state,session);state.activeProject=identity;state.view='build';state.pane=null;
    state.revision++;state.preview=null;state.previewRevision=-1;state.previewError='';state.drag=null;state.runtimeOutput='';state.runtimeServices=[];
    render();
  }finally{state.switching=false;$('app').inert=false;}
}
async function saveProjectFromOverview(identity) {
  if(state.saving||state.deleting)return;
  if(identity===state.activeProject){await saveAll();return;}
  const session=projectSessions.get(identity);if(!session)return;
  state.saving=true;updateStatus();renderMain();
  try {
    if(session.dirty){await api('/api/project',{project:session.project},identity);session.dirty=false;}
    for(const [path,draft] of session.drafts){
      if(!draft.dirty)continue;
      await api('/api/file',{path,content:draft.content},identity);draft.dirty=false;
    }
    state.projects=await api('/api/projects');notify('Project saved.');
  } finally {state.saving=false;updateStatus();renderMain();}
}
function renderProjects(content) {
  const welcome=el('div',undefined,'landing-intro');
  welcome.append(el('h2','Your next environment starts here.'),el('p','Create a Compose project, build it block by block, and keep its configuration files together.'));
  content.append(welcome);
  if(!state.projects.length){
    content.append(emptyState('Create your first project','Start with an empty project. You choose every service, image, and configuration block.',button('Create project',newProject,'primary','plus'),'build'));return;
  }
  content.append(sectionHeading('Your projects',state.projects.length));
  const list=el('div',undefined,'project-overview');
  for(const project of state.projects){
    const card=el('article',undefined,'project-overview-card');card.setAttribute('aria-label',project.name);card.dataset.projectId=project.id;
    const session=project.id===state.activeProject?state:projectSessions.get(project.id);
    const unsaved=session&&(session.dirty||[...session.drafts.values()].some(d=>d.dirty));
    const mark=el('div',undefined,'project-mark');mark.append(icon('build'));
    const description=el('div',undefined,'project-description');description.append(el('h2',project.name),el('p',unsaved?'Unsaved changes · save before closing':project.id===state.activeProject?'Current project':'Compose project','save-status'));
    card.append(mark,description);
    const actions=el('div',undefined,'project-card-actions');
    if(unsaved){const save=button('Save project',guarded(()=>saveProjectFromOverview(project.id)),'primary','check');save.disabled=state.saving||state.deleting;actions.append(save);}

    actions.append(button('Open',guarded(async()=>{await switchProject(project.id);if(project.id==='legacy'&&!state.project.children.length&&!state.dirty)await openSavedProject();navigate('build');}),'secondary','folder'),
      button('Rename',()=>renameProject(project),'tertiary','edit'),
      button('Delete',()=>deleteProject(project),'destructive','trash'));
    card.append(actions);list.append(card);
  }
  if(!state.projects.length)list.append(el('p','No saved projects yet. Create a project to get started.','empty-inline'));
  content.append(list);
}
function renameProject(project) {
  let input;
  openForm('Rename project','Change the display name. The Compose name, blocks, and files stay unchanged.',holder=>{
    const label=el('label','Project name','field-label');input=el('input');input.id='rename-project';input.value=project.name;input.maxLength=80;label.htmlFor=input.id;holder.append(label,input);
    return ()=>{input.setCustomValidity(input.value.trim()?'':'Enter a project name.');return input.reportValidity();};
  },'Save name',async()=>{
    const result=await api('/api/projects/rename',{action:'rename',id:project.id,name:input.value.trim()});
    state.projects=state.projects.map(p=>p.id===project.id?result:p);render();notify('Project renamed.');
  });
}
function deleteProject(project) {
  openForm('Delete project?',`“${project.name}” and all its saved blocks, files, folders, and unsaved edits will be permanently deleted. This cannot be undone.`,()=>{},'Delete permanently',async()=>{
    if(state.saving||state.deleting||state.runtimeBusy)throw new Error('Wait for the current file operation to finish.');
    state.deleting=true;++fileRequest;++previewRequest;
    try {
      await api('/api/projects/delete',{action:'delete',id:project.id});
      projectSessions.delete(project.id);state.projects=state.projects.filter(p=>p.id!==project.id);
      if(state.activeProject===project.id){
        Object.assign(state,{project:null,files:[],dirty:false,history:[],drafts:new Map(),file:'',filesExpanded:true,collapsed:new Set(),folders:new Set(),touched:new Set(),issues:[],validated:null,arriving:new Set()});
        state.activeProject=null;state.selected=null;state.pane=null;state.revision++;state.preview=null;state.previewRevision=-1;state.previewError='';
      }
      state.view='projects';render();notify('Project deleted.');
    } finally {state.deleting=false;updateStatus();}
  });
  $('form-dialog').querySelector('[type="submit"]').className='button danger';
  $('form-dialog').querySelector('.dialog-actions button').focus();
}
function newProject() {
  let input;
  openForm('New project','Choose a display name, such as Project 1. A Compose-compatible name is generated automatically. Each project has its own blocks and files.',holder=>{
    const label=el('label','Project name','field-label');input=el('input');input.id='new-project-name';label.htmlFor=input.id;input.maxLength=80;holder.append(label,input);
    return ()=>{input.setCustomValidity(input.value.trim()?'':'Enter a project name.');return input.reportValidity();};
  },'Create project',async()=>{
    if(state.saving||state.deleting||state.runtimeBusy)throw new Error('Wait for the current file operation to finish.');
    const project=await api('/api/projects',{name:input.value.trim()});state.projects.push(project);
    await switchProject(project.id);
  });
}
async function openSavedProject() {
  const revision=state.revision;
  const project=await api('/api/project');
  if(state.revision!==revision||state.dirty)return;
  state.project=project;state.history=[];state.selected=null;state.pane=null;
  state.revision++;state.preview=null;state.previewRevision=-1;state.previewError='';
  state.validated=null;state.issues=[];state.collapsed.clear();
  nodes().filter(node=>definition(node).op==='group').forEach(node=>state.collapsed.add(node.id));
  render();
  if(!project.children.length)notify('No saved blocks yet. Start by adding a project name and service.');
}
guarded(async()=>{
  [state.definitions,state.projects]=await Promise.all([api('/api/definitions'),api('/api/projects')]);
  state.project=null;state.activeProject=null;state.view='projects';
  state.ready=true;state.selected=null;
  nodes().filter(node=>definition(node).op==='group').forEach(node=>state.collapsed.add(node.id));
  render();
})();
