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
  document.querySelectorAll('.workspace button, #reset, #recover, #discard').forEach(button => button.disabled = value || (!!pendingDraft && !['recover','discard'].includes(button.id)));
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
  $('hints').replaceChildren(...lesson.hints.map(hint => {
    if (typeof hint === 'string') { const p = document.createElement('p'); p.textContent = hint; return p; }
    const card = document.createElement('article'); card.className = 'hint-card';
    const title = document.createElement('h3'); title.textContent = hint.title;
    const explanation = document.createElement('p'); explanation.textContent = hint.text;
    const language = document.createElement('span'); language.className = 'hint-language'; language.textContent = hint.language;
    const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = hint.code; pre.append(code);
    pre.tabIndex = 0; pre.setAttribute('aria-label', hint.title + ' code example');
    const task = document.createElement('p'); task.className = 'hint-task'; task.textContent = 'Your turn: ' + hint.task;
    card.append(title, explanation, language, pre, task); return card;
  }));
  $('lesson-help').open = false;
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
  $('progress-count').textContent = `${count}/6`; $('progress-fill').style.width = `${count / 6 * 100}%`;
  document.querySelector('[role=progressbar]').setAttribute('aria-valuenow', count);
  $('check-caption').textContent = state.completed[stage] ? 'Previously passed. Check again after editing.' : 'Test the current stage’s requirements.';
  setBusy(busy);
}
function changeStage(index) { if (busy || pendingDraft) return; stage=index; renderLesson(); $('mission-picker').open=false; cacheDraft(); }
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
  const previouslyCompleted = !!state.completed[stage];
  const result=await request('check',payload()); state=result.state;
  if(result.current) {clearDraft();$('save-status').textContent='All changes saved';}
  else {state.revision=result.checked_revision;cacheDraft();$('save-status').textContent='Conflict: newer save exists';}
  renderLesson();
  $('results').replaceChildren(...result.results.map(check=>{const li=document.createElement('li');li.className=check.passed?'pass':'fail';li.textContent=`${check.passed?'✓':'○'} ${check.label}`;if(!check.passed){const detail=document.createElement('small');detail.textContent=check.message;li.append(detail);}return li;}));
  const passed=result.results.every(item=>item.passed);
  $('check-caption').textContent=passed?'Stage complete. Keep building!':'Some requirements need another look.';
  if (result.current && passed) {
    notice('');
    if (!previouslyCompleted) showSuccess();
  } else {
    notice(result.current ? 'Your work is saved. Review the checkpoint feedback.' : 'The project changed during this check. Reload and check the current version.', !result.current);
  }
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
  selectFile(activeFile);renderLesson();$('recovery').hidden=true;pendingDraft=null;cacheDraft();notice('Draft recovered. If it is older than the saved version, download a backup before reloading.');setBusy(false);maybeTutorial();
};
$('discard').onclick=()=>{clearDraft();$('recovery').hidden=true;pendingDraft=null;setBusy(false);maybeTutorial();};

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
const endpointExamples = {
  '/api/info': {name:'Code4Fun teaching API', scope:'API container environment', endpoints:{'…':'See the fields below'}},
  '/api/username/': {username:'code4fun'},
  '/api/hostname/': {hostname:'code4fun-api'},
  '/api/ip': {addresses:['172.20.0.3']},
  '/api/metrics': {cpu_percent:12.5, memory_used_bytes:33554432, memory_limit_bytes:134217728, uptime_seconds:120.5}
};
const endpointDescriptions = {
  '/api/info':'Discover the available endpoints, field descriptions, and measurement scope.',
  '/api/username/':'The user running the API process.',
  '/api/hostname/':'The name of the API container.',
  '/api/ip':'Network addresses belonging to the API container.',
  '/api/metrics':'Current container measurements. Refresh around every five seconds.'
};
async function loadReference() {
  $('api-content').replaceChildren(element('p','Loading API reference…'));
  $('api-retry').hidden=true;
  try {
    const info=await request('reference');
    const intro=element('div');
    intro.append(element('p',info.scope),element('p','Use relative paths in script.js. All endpoints return JSON. The response examples below are illustrative; actual values change.'));
    const sections=[intro];
    for (const [path, fields] of Object.entries(info.endpoints)) {
      const section=element('section');
      const heading=element('h3');heading.append(element('span','GET','http-method'),element('code',path));
      section.append(heading,element('p',endpointDescriptions[path]||'Read JSON from this endpoint.'));
      const table=element('table',undefined,'api-fields');
      const head=element('thead');const header=element('tr');header.append(element('th','Field'),element('th','Meaning'));head.append(header);
      const body=element('tbody');
      const schema=path==='/api/info' ? {name:'API name',version:'Contract version',scope:'What environment the API describes',endpoints:'Supported paths and response fields',metrics:'Measurement source, availability, and sampling',trailing_slashes:'URL slash handling',errors:'Error response format'} : fields;
      for(const [field,description] of Object.entries(schema)) {
        const row=element('tr');const key=element('td');key.append(element('code',field));row.append(key,element('td',String(description)));body.append(row);
      }
      table.append(head,body);section.append(table,element('p','Example response','api-example-label'));
      const response=element('pre');response.append(element('code',JSON.stringify(endpointExamples[path]||{},null,2)));section.append(response);
      section.append(element('p','Try it in JavaScript','api-example-label'));
      const example=element('pre');example.append(element('code',`async function exploreApi() {
  const response = await fetch("${path}");
  if (!response.ok) throw new Error("Request failed");
  const data = await response.json();
  console.log(data);
}

exploreApi();`));section.append(example);
      section.append(element('p','Or use curl in a terminal','api-example-label'));
      const curl=element('pre');curl.append(element('code',`curl ${previewOrigin()}${path}`));section.append(curl);
      sections.push(section);
    }
    const measurements=element('section');measurements.append(element('h3','Measurements and missing values'));
    for(const key of ['source','cpu_sampling','unlimited_memory'])if(info.metrics?.[key])measurements.append(element('p',info.metrics[key]));
    measurements.append(element('p','A null measurement is unavailable; display N/A. Zero is a valid measurement. Uptime is in seconds, memory in bytes, and CPU usage in percent.'));
    const errors=element('section');errors.append(element('h3','When a request fails'),element('p','Check response.ok before reading the data. A 404 means the endpoint does not exist. A 502 from the preview means the API service could not be reached. Catch network errors too.'));
    sections.push(measurements,errors);$('api-content').replaceChildren(...sections);
  } catch(error) {
    $('api-content').replaceChildren(element('p',error.message));$('api-retry').hidden=false;
  }
}
function openReference() {if(!$('api-dialog').open)$('api-dialog').showModal();loadReference();}
$('api-link').onclick=openReference;
$('api-close').onclick=()=>$('api-dialog').close();
$('api-retry').onclick=loadReference;

let toastTimer, toastAnimation, toastQueue=0;
function dismissSuccess() {
  clearTimeout(toastTimer);toastAnimation?.cancel();$('success-toast').hidden=true;
  if(toastQueue){toastQueue--;showSuccess();}
}
function resumeToast() {
  if($('success-toast').hidden||!toastAnimation)return;
  toastAnimation.play();
  clearTimeout(toastTimer);toastTimer=setTimeout(dismissSuccess,Math.max(0,6000-Number(toastAnimation.currentTime||0)));
}
function pauseToast() {clearTimeout(toastTimer);toastAnimation?.pause();}
function showSuccess() {
  if(!$('success-toast').hidden){toastQueue++;return;}
  $('success-toast').hidden=false;
  toastAnimation=$('toast-duration').animate([{transform:'scaleX(1)'},{transform:'scaleX(0)'}],{duration:6000,fill:'forwards'});
  resumeToast();
}
$('toast-close').onclick=dismissSuccess;
$('success-toast').addEventListener('mouseenter',pauseToast);
$('success-toast').addEventListener('mouseleave',()=>{if(!$('success-toast').contains(document.activeElement))resumeToast();});
$('success-toast').addEventListener('focusin',pauseToast);
$('success-toast').addEventListener('focusout',event=>{if(!$('success-toast').contains(event.relatedTarget)&&!$('success-toast').matches(':hover'))resumeToast();});

let tourStep=0, tourOriginal, tourPositionFrame, tourActionBusy=false;
const courseTopics=[
  {name:'HTML',subtitle:'Structure your page',language:'HTML',
   title:'HTML: the foundation of a website',
   text:'HTML stands for HyperText Markup Language. It gives a webpage its structure and meaning. Tags identify headings, paragraphs, buttons, and other content. Here, h2 creates a heading and p creates a paragraph.',
   code:'<h2>My reading list</h2>\n<p>A place for books I want to read.</p>',
   preview:()=>{const block=element('div');block.append(element('h2','My reading list'),element('p','A place for books I want to read.'));return block;}},
  {name:'CSS',subtitle:'Give it a style',language:'CSS',
   title:'CSS: decide how the page looks',
   text:'CSS stands for Cascading Style Sheets. A selector chooses an HTML element; the declarations inside its braces change its appearance. This is the same heading with a different color and some space around it.',
   code:'h2 {\n  color: #8b3c62;\n  background-color: #fbeaf0;\n  padding: 12px;\n}',
   preview:()=>{const block=element('div');block.append(element('h2','My reading list','demo-styled'),element('p','The words are the same. CSS changes their presentation.'));return block;}},
  {name:'JavaScript',subtitle:'Make it respond',language:'JavaScript',
   title:'JavaScript: make something happen',
   text:'JavaScript adds behavior. It can listen for a click and update the page without reloading it. Try the button: the event listener changes the message each time you click.',
   code:'const button = document.querySelector("#add-book");\nlet count = 0;\nbutton.addEventListener("click", () => {\n  count += 1;\n  document.querySelector("#book-count")\n    .textContent = `Books added: ${count}`;\n});',
   preview:()=>{let count=0;const block=element('div');const button=element('button','Add a book','secondary');const message=element('p','Books added: 0');message.setAttribute('aria-live','polite');button.onclick=()=>{count++;message.textContent=`Books added: ${count}`;};block.append(button,message);return block;}},
  {name:'APIs',subtitle:'Read real data',language:'JavaScript · API request',
   title:'APIs: ask a server for information',
   text:'API stands for Application Programming Interface. Your JavaScript can send an HTTP request to a server and read its response as JSON. Try requesting the description of our prepared API. Its measurements describe the API container, not your laptop.',
   code:'async function describeApi() {\n  const response = await fetch("/api/info");\n  if (!response.ok) throw new Error("Request failed");\n  const info = await response.json();\n  console.log(info.name);\n}\ndescribeApi();',
   preview:()=>{const block=element('div');const button=element('button','Fetch API info','secondary');const result=element('p','No request sent yet.','demo-api-result');result.setAttribute('aria-live','polite');button.onclick=async()=>{button.disabled=true;result.textContent='Loading…';try{const info=await request('reference');if(!block.isConnected)return;result.textContent=info.name;}catch(error){if(block.isConnected)result.textContent='Request failed. Check the API service, then try again.';}finally{button.disabled=false;}};block.append(button,result);return block;}}
];
const tourSteps=[
  {title:'This is the course you’ll go through',text:'You will build one dashboard, adding a new skill at each stage. First, let’s explore the four building blocks below. Each topic has a small example you can see or try.'},
  ...courseTopics.map((topic,index)=>({title:topic.title,text:topic.text,topic:index})),
  {title:'Choose a mission',text:'Open Missions here to choose your task. Only these instructions change; your files and preview stay as they are. The help section includes examples you can adapt.',target:'mission-picker'},
  {title:'Work in your files',text:'Use these tabs to switch between HTML, CSS, and JavaScript. They all belong to the same project. Try opening your stylesheet, then return to HTML when you are ready.',target:'files',action:'Open style.css',try:()=>selectFile('style.css')},
  {title:'Run your website',text:'Run preview shows your current edits in the Preview panel. You can try your buttons and see what your code does. Running does not save your files.',target:'run',action:'Run preview',try:()=>run()},
  {title:'Save your work',text:'Save project keeps all three files and your selected mission for next time. You can also press Ctrl+S or ⌘S. The label at the top of the editor tells you whether you have unsaved changes.',target:'save'},
  {title:'Check the current mission',text:'Check my work saves your project and tests the task requirements. Feedback shows what works and what still needs attention. Passing a mission records your progress; you can keep refining the same project.',target:'check'},
  {title:'Keep the API reference close',text:'When you reach the API missions, use this reference for endpoints, field descriptions, and request examples. You can replay this tutorial at any time with Tutorial.',target:'api-link',action:'Open API reference',try:openReference}
];
function tourTarget() {
  const step=tourSteps[tourStep];
  if(!step.target)return null;
  return $(step.target==='mission-picker'&&innerWidth<=700?'mission-summary':step.target);
}
function positionTour() {
  if(!$('tutorial-dialog').open)return;
  const target=tourTarget(),dialog=$('tutorial-dialog');
  if(!target){dialog.style.left='';dialog.style.top='';$('tour-spotlight').hidden=true;return;}
  const r=target.getBoundingClientRect();
  const spotlight=$('tour-spotlight');spotlight.hidden=false;
  Object.assign(spotlight.style,{left:`${r.left-4}px`,top:`${r.top-4}px`,width:`${r.width+8}px`,height:`${r.height+8}px`});
  const width=dialog.getBoundingClientRect().width,height=$('tutorial-card').getBoundingClientRect().height;
  const gap=16,pad=12;
  const clamp=(n,min,max)=>Math.max(min,Math.min(n,Math.max(min,max)));
  const cx=clamp(r.left+(r.width-width)/2,pad,innerWidth-width-pad);
  const cy=clamp(r.top+(r.height-height)/2,pad,innerHeight-height-pad);
  const candidates=[
    {x:r.right+gap,y:cy}, {x:r.left-width-gap,y:cy},
    {x:cx,y:r.bottom+gap}, {x:cx,y:r.top-height-gap}
  ];
  const fits=p=>p.x>=pad&&p.y>=pad&&p.x+width<=innerWidth-pad&&p.y+height<=innerHeight-pad;
  let point=candidates.find(fits);
  if(!point){
    // On small screens keep the tip above or below the highlighted control.
    const below=innerHeight-r.bottom,above=r.top;
    point={x:cx,y:below>=above?clamp(r.bottom+gap,pad,innerHeight-height-pad):clamp(r.top-height-gap,pad,innerHeight-height-pad)};
  }
  dialog.style.left=`${point.x}px`;dialog.style.top=`${point.y}px`;
}
function scheduleTourPosition() {
  cancelAnimationFrame(tourPositionFrame);tourPositionFrame=requestAnimationFrame(positionTour);
}
window.addEventListener('resize',scheduleTourPosition);
window.addEventListener('scroll',scheduleTourPosition,true);
new ResizeObserver(scheduleTourPosition).observe($('tutorial-card'));
const tutorialMotion = matchMedia('(prefers-reduced-motion: reduce)');
let tutorialAnimations = [];
function animateTutorialStep() {
  tutorialAnimations.forEach(animation=>animation.cancel());
  tutorialAnimations=[];
  if(tutorialMotion.matches)return;
  for(const id of ['tutorial-title','tutorial-text','tutorial-example']) {
    if($(id).hidden)continue;
    tutorialAnimations.push($(id).animate(
      [{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],
      {duration:180,easing:'cubic-bezier(.2,.7,.3,1)'}
    ));
  }
}
tutorialMotion.addEventListener('change',event=>{
  if(event.matches){tutorialAnimations.forEach(animation=>animation.cancel());tutorialAnimations=[];}
});
function renderTour() {
  document.querySelectorAll('.tour-target').forEach(node=>node.classList.remove('tour-target'));
  const step=tourSteps[tourStep],isCourse=!step.target;
  $('tutorial-dialog').classList.toggle('anchored',!isCourse);
  $('tutorial-count').textContent=`${tourStep+1} of ${tourSteps.length}`;
  $('tutorial-title').textContent=step.title;$('tutorial-text').textContent=step.text;
  $('tutorial-topics').hidden=!isCourse;
  if (!$('tutorial-topics').children.length) {
    $('tutorial-topics').replaceChildren(...courseTopics.map((topic,index)=>{
      const card=element('button',undefined,'topic-card');
      card.append(element('strong',topic.name),element('span',topic.subtitle));
      card.onclick=()=>{if(tourActionBusy)return;tourStep=index+1;renderTour();};return card;
    }));
  }
  [...$('tutorial-topics').children].forEach((card,index)=>{
    if(step.topic===index)card.setAttribute('aria-current','step');
    else card.removeAttribute('aria-current');
  });
  $('tutorial-example').hidden=step.topic===undefined;
  if(step.topic!==undefined){
    const topic=courseTopics[step.topic];$('example-language').textContent=topic.language;
    $('example-code').textContent=topic.code;$('example-preview').replaceChildren(topic.preview());
  }else{$('example-preview').replaceChildren();}
  $('tutorial-back').disabled=tourStep===0;
  $('tutorial-next').textContent=tourStep===tourSteps.length-1?'Start coding':'Next';
  $('tutorial-try').hidden=!step.action;$('tutorial-try').textContent=step.action||'';
  $('tutorial-error').textContent='';$('tutorial-card').scrollTop=0;
  if(step.target){
    $('mission-picker').open=step.target==='mission-picker'?true:tourOriginal.missionsOpen;
    const target=tourTarget();target.classList.add('tour-target');
    target.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});
  }
  scheduleTourPosition();
  animateTutorialStep();
}
function startTutorial() {
  if(busy||pendingDraft||!state||$('tutorial-dialog').open)return;
  tourOriginal={file:activeFile,missionsOpen:$('mission-picker').open,lessonScroll:document.querySelector('.lesson-body').scrollTop,x:scrollX,y:scrollY};
  tourStep=0;renderTour();$('tutorial-dialog').showModal();positionTour();
}
function maybeTutorial() {if(state&&!state.tutorial_seen&&!pendingDraft&&!busy)startTutorial();}
async function finishTutorial() {
  if(tourActionBusy)return;
  tourActionBusy=true;$('tutorial-next').disabled=true;$('tutorial-skip').disabled=true;$('tutorial-back').disabled=true;
  try {
    await request('tutorial',{});state.tutorial_seen=true;
    $('tutorial-dialog').close();tutorialAnimations.forEach(animation=>animation.cancel());document.querySelectorAll('.tour-target').forEach(node=>node.classList.remove('tour-target'));
    if(tourOriginal){selectFile(tourOriginal.file);$('mission-picker').open=tourOriginal.missionsOpen;document.querySelector('.lesson-body').scrollTop=tourOriginal.lessonScroll;window.scrollTo({left:tourOriginal.x,top:tourOriginal.y,behavior:'instant'});}
    $('tutorial-open').focus({preventScroll:true});
  } catch(error) {$('tutorial-error').textContent=error.message;}
  finally {tourActionBusy=false;$('tutorial-next').disabled=false;$('tutorial-skip').disabled=false;$('tutorial-back').disabled=tourStep===0;}
}
$('tutorial-open').onclick=startTutorial;
$('tutorial-next').onclick=()=>{if(tourActionBusy)return;if(tourStep===tourSteps.length-1)finishTutorial();else{tourStep++;renderTour();}};
$('tutorial-back').onclick=()=>{if(!tourActionBusy&&tourStep>0){tourStep--;renderTour();}};
$('tutorial-skip').onclick=finishTutorial;
$('tutorial-dialog').addEventListener('cancel',event=>{event.preventDefault();finishTutorial();});
$('tutorial-try').onclick=async()=>{
  if(tourActionBusy)return;tourActionBusy=true;
  $('tutorial-try').disabled=true;$('tutorial-next').disabled=true;$('tutorial-back').disabled=true;$('tutorial-skip').disabled=true;
  try{await tourSteps[tourStep].try();}catch(error){$('tutorial-error').textContent=error.message;}
  finally{tourActionBusy=false;$('tutorial-try').disabled=false;$('tutorial-next').disabled=false;$('tutorial-back').disabled=tourStep===0;$('tutorial-skip').disabled=false;scheduleTourPosition();}
};
async function boot() {
  setBusy(true);
  try {
    const result=await request('project');lessons=result.stages;state=result;previewPort=result.preview_port;files={...state.files};stage=state.stage;
    for (const name of Object.keys(files)) {const button=document.createElement('button');button.textContent=name;button.dataset.file=name;button.setAttribute('role','tab');button.onclick=()=>selectFile(name);button.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const list=Object.keys(files);const next=list[(list.indexOf(activeFile)+(event.key==='ArrowRight'?1:2))%3];selectFile(next);[...$('files').children].find(el=>el.dataset.file===next).focus();}});$('files').append(button);}
    selectFile(activeFile);renderLesson();$('save-status').textContent='All changes saved';
    try {
      const draft=JSON.parse(localStorage.getItem(draftKey));
      if(draft && draft.files && Object.keys(draft.files).sort().join()===Object.keys(files).sort().join() && Object.values(draft.files).every(v=>typeof v==='string') && Number.isInteger(draft.stage) && draft.stage>=0 && draft.stage<6 && typeof draft.revision==='string' && (JSON.stringify(draft.files)!==JSON.stringify(files)||draft.stage!==stage)) {
        pendingDraft=draft;$('recovery').hidden=false;$('recovery-detail').textContent=draft.revision===state.revision?'Recover your unsaved edits or keep the saved project.':'This draft is based on an older save. Recovery preserves that conflict; download it before reloading.';
      }
    } catch (_) {}
    await run();
  } catch(error) {notice('Could not open Code4Fun: '+error.message,true);}
  finally {setBusy(false);maybeTutorial();}
}
boot();
