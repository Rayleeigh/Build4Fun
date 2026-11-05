'use strict';
const $ = id => document.getElementById(id);
const draftKey = `code4fun:draft:${location.origin}`;
let state, lessons, files, previewPort, stage = 0, activeFile = 'index.html', busy = false, pendingDraft;
const names = ['HTML', 'HTML + CSS', 'HTML + JavaScript', 'All three together', 'Your first API', 'Live dashboard'];
function notice(message, error = false) { $('notice').textContent = message; $('notice').className = error ? 'error' : ''; }
async function request(path, data) {
  const response = await fetch('/code4fun/api/' + path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status}).`);
  return body;
}
function payload() { return {files, stage, revision:state.revision}; }
function cacheDraft() {
  try { localStorage.setItem(draftKey, JSON.stringify(payload())); }
  catch (_) { notice('Browser draft storage is unavailable. Use Save project or download a backup.', true); }
  $('save-status').textContent = 'Unsaved changes';
}
function clearDraft() { try { localStorage.removeItem(draftKey); } catch (_) {} }
function setBusy(value) {
  busy = value;
  document.querySelectorAll('button').forEach(button => button.disabled = value || (!!pendingDraft && !['recover','discard'].includes(button.id)));
  $('code').readOnly = value || !!pendingDraft;
  if (!value && !pendingDraft) { $('previous').disabled = stage === 0; $('next').disabled = stage === 5; }
}
function lines() { $('line-numbers').textContent = Array.from({length:$('code').value.split('\n').length}, (_, i) => i+1).join('\n'); }
function selectFile(name) {
  activeFile = name; $('code').value = files[name]; $('editor-label').textContent = 'Editing ' + name;
  for (const button of $('files').children) { button.setAttribute('aria-selected', String(button.dataset.file === name)); button.tabIndex = button.dataset.file === name ? 0 : -1; }
  lines();
}
function renderLesson() {
  const lesson = lessons[stage];
  $('focus').textContent = lesson.focus; $('stage-number').textContent = `${stage+1} / 6`;
  $('lesson-title').textContent = lesson.title; $('goal').textContent = lesson.goal;
  $('steps').replaceChildren(...lesson.steps.map(text => {const li = document.createElement('li'); li.textContent = text; return li;}));
  $('hints').replaceChildren(...lesson.hints.map(text => {const p = document.createElement('p'); p.textContent = text; return p;}));
  document.querySelector('details').open = false;
  $('stages').replaceChildren(...names.map((name, index) => {
    const button = document.createElement('button');
    const number = document.createElement('span'); number.className = 'stage-index'; number.textContent = state.completed[index] ? '✓' : index+1;
    const label = document.createElement('span'); label.className = 'stage-label'; label.textContent = name;
    button.append(number,label); button.setAttribute('aria-label', `Stage ${index+1}: ${name}${state.completed[index] ? ', previously completed' : ''}`);
    if (stage === index) button.setAttribute('aria-current','step');
    button.onclick = () => changeStage(index); return button;
  }));
  $('results').replaceChildren(...lesson.checks.map(text => {const li=document.createElement('li');li.textContent='○ '+text;return li;}));
  const count = Object.keys(state.completed).length;
  $('progress-count').textContent = `${count} / 6`; $('progress-fill').style.width = `${count / 6 * 100}%`;
  $('check-caption').textContent = state.completed[stage] ? 'Previously passed. Check again after editing.' : 'Test the current stage’s requirements.';
  setBusy(busy);
}
function changeStage(index) { if (busy || pendingDraft) return; stage=index; renderLesson(); cacheDraft(); }
function previewOrigin() { return `http://${location.hostname}:${previewPort}`; }
async function run() {
  const result = await request('run', {files});
  $('preview').src = previewOrigin() + result.path;
}
async function perform(action) {
  if (busy || pendingDraft) return;
  setBusy(true); notice('');
  try { await action(); } catch (error) { notice(error.message, true); }
  finally { setBusy(false); }
}
async function save() {
  state = await request('save', payload()); clearDraft(); $('save-status').textContent = 'All changes saved'; notice('Project saved.');
}
$('code').addEventListener('input', () => {files[activeFile]=$('code').value;lines();cacheDraft();$('check-caption').textContent='Code changed. Run checks again.';});
$('code').addEventListener('scroll', () => {$('line-numbers').scrollTop=$('code').scrollTop;});
$('code').addEventListener('keydown', event => {
  if(event.key==='Tab' && !event.shiftKey) {event.preventDefault();const el=$('code');el.setRangeText('  ',el.selectionStart,el.selectionEnd,'end');el.dispatchEvent(new Event('input'));}
});
document.addEventListener('keydown', event => {if((event.ctrlKey||event.metaKey)&&event.key==='s'){event.preventDefault();if(state) perform(save);}});
$('save').onclick = () => perform(save);
$('run').onclick = $('rerun').onclick = () => perform(async () => {await run();notice('Preview updated from your current edits.');});
$('previous').onclick=()=>changeStage(Math.max(0,stage-1)); $('next').onclick=()=>changeStage(Math.min(5,stage+1));
$('check').onclick=()=>perform(async()=>{
  $('check-caption').textContent='Saving and testing your dashboard…'; notice('Checking your work. The final stage can take up to a minute.');
  const result=await request('check',payload()); state=result.state;
  if(result.current) {clearDraft();$('save-status').textContent='All changes saved';}
  else {state.revision=result.checked_revision;cacheDraft();$('save-status').textContent='Conflict: newer save exists';}
  renderLesson();
  $('results').replaceChildren(...result.results.map(check=>{const li=document.createElement('li');li.className=check.passed?'pass':'fail';li.textContent=`${check.passed?'✓':'○'} ${check.label}`;if(!check.passed){const detail=document.createElement('small');detail.textContent=check.message;li.append(detail);}return li;}));
  const passed=result.results.every(item=>item.passed);
  $('check-caption').textContent=passed?'Stage complete. Keep building!':'Some requirements need another look.';
  notice(result.current ? (passed?'Checkpoint passed! Your progress is saved.':'Your work is saved. Review the checkpoint feedback.') : 'The project changed during this check. Reload and check the current version.', !result.current);
});
$('reset').onclick=()=>{
  if(!confirm('Reset the entire dashboard? This replaces all three files with the original starter files and clears all six stages of progress. Download a backup first if needed.'))return;
  perform(async()=>{state=await request('reset',{revision:state.revision});files={...state.files};stage=0;clearDraft();$('recovery').hidden=true;renderLesson();selectFile(activeFile);await run();$('save-status').textContent='All changes saved';notice('Project reset to its starting point.');});
};
$('download').onclick=()=>{
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify({files,stage},null,2)],{type:'application/json'}));link.download='my-server-dashboard.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
};
$('recover').onclick=()=>{
  files={...pendingDraft.files};stage=pendingDraft.stage;
  // Preserve the original revision: recovering an old draft must not bypass conflicts.
  state.revision=pendingDraft.revision;
  selectFile(activeFile);renderLesson();$('recovery').hidden=true;pendingDraft=null;cacheDraft();notice('Draft recovered. If it is older than the saved version, download a backup before reloading.');setBusy(false);
};
$('discard').onclick=()=>{clearDraft();$('recovery').hidden=true;pendingDraft=null;setBusy(false);};
async function boot() {
  setBusy(true);
  try {
    const result=await request('project');lessons=result.stages;state=result;previewPort=result.preview_port;files={...state.files};stage=state.stage;
    for (const name of Object.keys(files)) {const button=document.createElement('button');button.textContent=name;button.dataset.file=name;button.setAttribute('role','tab');button.onclick=()=>selectFile(name);button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const list=Object.keys(files);const next=list[(list.indexOf(activeFile)+(event.key==='ArrowRight'?1:2))%3];selectFile(next);[...$('files').children].find(el=>el.dataset.file===next).focus();}});$('files').append(button);}
    selectFile(activeFile);renderLesson();$('save-status').textContent='All changes saved';
    $('api-link').href=previewOrigin()+'/api/info';
    try {
      const draft=JSON.parse(localStorage.getItem(draftKey));
      if(draft && draft.files && Object.keys(draft.files).sort().join()===Object.keys(files).sort().join() && Object.values(draft.files).every(v=>typeof v==='string') && Number.isInteger(draft.stage) && draft.stage>=0 && draft.stage<6 && typeof draft.revision==='string' && (JSON.stringify(draft.files)!==JSON.stringify(files)||draft.stage!==stage)) {
        pendingDraft=draft;$('recovery').hidden=false;$('recovery-detail').textContent=draft.revision===state.revision?'Recover your unsaved edits or keep the saved project.':'This draft is based on an older save. Recovery preserves that conflict; download it before reloading.';
      }
    } catch (_) {}
    await run();
  } catch(error) {notice('Could not open Code4Fun: '+error.message,true);}
  finally {setBusy(false);}
}
boot();
