'use strict';
const $=id=>document.getElementById(id);
let state,logApp,pending=new Set();
const cards=new Map();
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function makeCard(app){
  const card=node('article',undefined,'app '+app.id),top=node('div',undefined,'card-top'),symbol=node('div',app.title[0]+'4','symbol');
  top.append(symbol,node('span','Checking…','status'));card.append(top,node('h2',app.title),node('p',app.description,'description'));
  const form=node('div',undefined,'options'),label=node('label','Launch from'),source=node('select');source.id='source-'+app.id;label.htmlFor=source.id;
  for(const [value,title] of [['local','Local build'],['registry','GitHub Container Registry']]){const option=node('option',title);option.value=value;source.append(option);}
  const tagLabel=node('label','Image tag'),tag=node('input');tag.id='tag-'+app.id;tagLabel.htmlFor=tag.id;tag.value='latest';tag.maxLength=128;tag.spellcheck=false;tag.autocomplete='off';tagLabel.hidden=tag.hidden=true;
  source.onchange=()=>{tagLabel.hidden=tag.hidden=source.value!=='registry';};form.append(label,source,tagLabel,tag);
  const archHeading=node('div',undefined,'architecture-label'),archLabel=node('label','Architecture'),architecture=node('select'),info=node('button','i','architecture-info');
  architecture.id='architecture-'+app.id;archLabel.htmlFor=architecture.id;info.type='button';info.setAttribute('aria-label','About CPU architectures');info.onclick=()=>$('architecture-help').showModal();archHeading.append(archLabel,info);
  for(const [value,title] of [['','Choose architecture…'],['arm64','ARM64'],['amd64','AMD64']]){const option=node('option',title);option.value=value;architecture.append(option);}
  architecture.required=true;architecture.onchange=render;form.append(archHeading,architecture);card.append(form);
  const actions=node('div',undefined,'actions'),start=node('button','Start','primary'),stop=node('button','Stop','secondary'),open=node('a','Open app ↗','open');open.target='_blank';open.rel='noopener';
  start.onclick=()=>act(app.id,'start');stop.onclick=()=>act(app.id,'stop');actions.append(start,stop,open);card.append(actions);
  const bottom=node('div',undefined,'card-bottom'),detail=node('span',''),logs=node('button','Activity','quiet');logs.onclick=()=>{logApp=app.id;$('logs').showModal();renderLog();};bottom.append(detail,logs);card.append(bottom);
  cards.set(app.id,{card,source,tag,architecture,status:top.lastChild,start,stop,open,detail});return card;
}
async function act(app,action){
  const c=cards.get(app);if(pending.has(app)||state.jobs[app]?.running)return;
  pending.add(app);render();
  try{
    const response=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({app,action,source:c.source.value,tag:c.tag.value,architecture:c.architecture.value})});
    const result=await response.json();if(!response.ok)throw new Error(result.error);
    state.jobs[app]=result;logApp=app;if(!$('logs').open)$('logs').showModal();renderLog();
  }catch(error){$('error').hidden=false;$('error').textContent=error.message;}
  finally{pending.delete(app);render();}
}
function render(){
  if(!state)return;$('engine').textContent=state.docker?'Docker needs attention':'Docker connected';
  for(const app of state.apps){
    if(!cards.has(app.id))$('apps').append(makeCard(app));
    const c=cards.get(app.id),job=state.jobs[app.id],working=!!job?.running||pending.has(app.id);
    const label=working?(job?.action==='stop'?'Stopping…':job?.source==='registry'?'Pulling & starting…':'Building & starting…'):({running:'Running',stopped:'Stopped',partial:'Partly running',starting:'Starting…',unhealthy:'Needs attention',unavailable:'Unavailable'}[app.status]||'Checking…');
    c.status.textContent=label;c.status.className='status '+(working?'working':app.status);
    c.start.disabled=working||app.status==='unavailable'||!c.architecture.value;c.architecture.disabled=working;c.stop.disabled=working||!['running','partial','starting','unhealthy'].includes(app.status);c.source.disabled=working;c.tag.disabled=working;
    c.start.textContent=app.status==='running'?'Update & start':'Start';
    c.open.href='http://'+location.hostname+':'+app.port;c.open.hidden=!['running','partial','starting','unhealthy'].includes(app.status);
    c.detail.textContent=job?.exit_code===1&&!working?'Last operation failed. See Activity.':app.error?'Check Docker and repository access.':working?'This can take a few minutes.':app.status==='running'?'localhost:'+app.port:'Ready when you are.';
  }
  renderLog();
}
function renderLog(){
  if(!logApp||!$('logs').open)return;
  const app=state.apps.find(a=>a.id===logApp),job=state.jobs[logApp];$('log-title').textContent=app.title+' · Activity';
  $('log-status').textContent=!job?'No launcher activity yet.':job.running?'Working… You can close this window and keep browsing.':job.exit_code===0?'Complete':'Operation failed. Review the output below.';
  const output=$('log-output'),nearBottom=output.scrollTop+output.clientHeight>=output.scrollHeight-30;output.textContent=job?.log||'Start or stop this app to see its output here.';if(nearBottom)output.scrollTop=output.scrollHeight;
}
$('close-architecture-help').onclick=()=>$('architecture-help').close();
$('close-logs').onclick=()=>$('logs').close();
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw new Error('Could not reach the launcher.');state=await response.json();render();}catch(error){$('engine').textContent='Launcher unavailable';$('error').textContent=error.message;$('error').hidden=false;}}
refresh();setInterval(refresh,1500);
