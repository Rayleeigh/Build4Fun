'use strict';
const $=id=>document.getElementById(id);
let state,active,selected={},hintCounts={},busy=false,pollTimer,toastTimer;
const terminals=new Map();
function node(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
function notice(text,error=false){$('notice').textContent=text;$('notice').className=error?'error':'';}
async function api(path,data){const response=await fetch('/api/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const body=await response.json();if(!response.ok)throw new Error(body.error||'Request failed');return body;}
function program(){return state.programs.find(p=>p.id===active);}
function challenge(){return program().challenges.find(c=>c.id===selected[active]);}
function render(){
  const p=program();if(!selected[active])selected[active]=(p.challenges.find(c=>!state.completed[c.id])||p.challenges[0]).id;
  $('programs').replaceChildren(...state.programs.map(p=>{const b=node('button');b.append(node('span',p.title),node('small',p.challenges.filter(c=>state.completed[c.id]).length+'/'+p.challenges.length));if(p.id===active)b.setAttribute('aria-current','page');b.onclick=()=>switchProgram(p.id);return b;}));
  $('program-title').textContent=p.title;$('difficulty').textContent=p.difficulty;$('description').textContent=p.description;
  const count=p.challenges.filter(c=>state.completed[c.id]).length;$('progress-count').textContent=count+'/'+p.challenges.length;$('progress').max=p.challenges.length;$('progress').value=count;$('challenge-count').textContent=p.challenges.length;
  $('challenges').replaceChildren(...p.challenges.map((c,index)=>{const b=node('button');b.append(node('span',state.completed[c.id]?'✓':String(index+1),'challenge-number'),node('span',c.title));if(c.id===selected[active])b.setAttribute('aria-current','step');b.onclick=()=>{if(busy)return;selected[active]=c.id;renderTask();render();};return b;}));
  const evidence={'forensics':['01-message.hex','02-recovered.dat','03-workshop-photo.jpg','04-support-bundle.bin','05-account.sha256','06-records.zip'],'network-analysis':['support-session.pcap','topology.txt']};
  $('downloads').hidden=!evidence[active];
  $('download-links').replaceChildren(...(evidence[active]||[]).map(name=>{const a=node('a',name);a.href='/api/download?program='+encodeURIComponent(active)+'&file='+encodeURIComponent(name);a.download=name;return a;}));
  $('portal-view').hidden=active!=='web-api';$('prepare').hidden=!!state.ready[active];renderTask();
}
function renderTask(){const c=challenge();$('task-title').textContent=c.title;$('goal').textContent=c.goal;$('start').textContent=program().start;$('flag').value='';$('feedback').textContent=state.completed[c.id]?'Previously completed.':'';$('feedback').className='';$('hints').replaceChildren(...c.hints.slice(0,hintCounts[c.id]||0).map(text=>node('p',text)));$('hint').disabled=(hintCounts[c.id]||0)>=c.hints.length;$('hint').textContent=$('hint').disabled?'All hints shown':'Show next hint';}
$('hint').onclick=()=>{const c=challenge();hintCounts[c.id]=Math.min(c.hints.length,(hintCounts[c.id]||0)+1);const value=$('flag').value;renderTask();$('flag').value=value;};
function showTerminalView(){ $('terminal-area').hidden=false;$('portal').hidden=true;$('terminal-view').setAttribute('aria-pressed','true');$('portal-view').setAttribute('aria-pressed','false');requestAnimationFrame(fit); }
$('terminal-view').onclick=showTerminalView;
$('portal-view').onclick=()=>{if(active!=='web-api')return;$('terminal-area').hidden=true;$('portal').hidden=false;$('terminal-view').setAttribute('aria-pressed','false');$('portal-view').setAttribute('aria-pressed','true');$('portal').src=`http://${location.hostname}:${state.portal_port}/`;};
async function switchProgram(id){if(busy||id===active)return;busy=true;clearTimeout(pollTimer);try{await api('activate',{program:id});active=id;state.active=id;document.querySelector('.shell').classList.remove('nav-open');for(const [key,t] of terminals)t.host.hidden=key!==active;showTerminalView();render();await connect();}catch(error){notice(error.message,true);}finally{busy=false;}}
function encode(text){return btoa(String.fromCharCode(...new TextEncoder().encode(text)));}
function terminalCall(t,action,extra={}){return api('terminal',{program:t.program,terminal:t.id,action,...extra});}
async function connect(){
  if(!state.ready[active]){$('connection').textContent='Preparing…';notice(state.errors[active]||'Preparing program files. Retry when the service is ready.');return;}
  let t=terminals.get(active);
  if(!t){
    const host=node('div',undefined,'terminal-host');host.setAttribute('aria-label',program().title+' terminal');$('terminal-area').append(host);
    const term=new Terminal({fontFamily:'ui-monospace, SFMono-Regular, Menlo, monospace',fontSize:12,lineHeight:1.35,cursorBlink:true,convertEol:false,scrollback:5000,screenReaderMode:true,theme:{background:'#17171b',foreground:'#e8e8ed',cursor:'#fafafa',selectionBackground:'#55555f'}});term.open(host);
    t={program:active,host,term,id:null,cursor:0,input:Promise.resolve(),dimensions:''};terminals.set(active,t);
    term.onData(data=>{if(!t.id)return;t.input=t.input.then(()=>terminalCall(t,'input',{input:encode(data)})).catch(error=>{if(active===t.program)notice(error.message,true);});});
    term.writeln('Connecting to '+program().title+'…');
  }
  for(const [key,item] of terminals)item.host.hidden=key!==active;
  try{
    if(!t.id){let old;try{old=sessionStorage.getItem('crack4fun:terminal:'+active);}catch(_){}t.id=old||(await api('terminal',{program:active,action:'open'})).terminal;try{sessionStorage.setItem('crack4fun:terminal:'+active,t.id);}catch(_){} }
    $('connection').textContent='Connected';notice('');fit();poll(t);
  }catch(error){$('connection').textContent='Disconnected';notice(error.message,true);}
}
function fit(){const t=terminals.get(active);if(!t||t.host.hidden||$('terminal-area').hidden)return;const measure=node('span','M');Object.assign(measure.style,{position:'absolute',visibility:'hidden',font:'12px ui-monospace,SFMono-Regular,Menlo,monospace'});t.host.append(measure);const width=measure.getBoundingClientRect().width;measure.remove();const cols=Math.max(20,Math.floor((t.host.clientWidth-26)/width));const rows=Math.max(10,Math.floor((t.host.clientHeight-25)/(12*1.35)));const key=cols+':'+rows;if(key===t.dimensions)return;t.dimensions=key;t.term.resize(cols,rows);if(t.id)terminalCall(t,'resize',{cols,rows}).catch(()=>{});}
new ResizeObserver(fit).observe($('terminal-area'));window.addEventListener('resize',fit);
async function poll(t){clearTimeout(pollTimer);if(t.program!==active||!t.id)return;try{const response=await terminalCall(t,'poll',{cursor:t.cursor});if(t.program!==active)return;t.cursor=response.cursor;if(response.output)t.term.write(Uint8Array.from(atob(response.output),c=>c.charCodeAt(0)));if(response.closed){$('connection').textContent='Session ended';return;}$('connection').textContent='Connected';pollTimer=setTimeout(()=>poll(t),180);}catch(error){$('connection').textContent='Disconnected';notice(error.message+' Use Restart terminal to reconnect.',true);}}
$('restart-terminal').onclick=async()=>{if(!confirm('Restart this terminal? Running commands will stop. Files and progress stay unchanged.'))return;const t=terminals.get(active);clearTimeout(pollTimer);if(t){try{if(t.id)await terminalCall(t,'close');}catch(_){}t.term.dispose();t.host.remove();terminals.delete(active);}try{sessionStorage.removeItem('crack4fun:terminal:'+active);}catch(_){}await connect();};
$('flag-form').onsubmit=async event=>{event.preventDefault();if(busy)return;busy=true;$('submit').disabled=true;try{const response=await api('submit',{program:active,challenge:challenge().id,flag:$('flag').value});state.completed=response.state.completed;render();$('feedback').textContent=response.message;$('feedback').className=response.correct?'':'error';if(response.correct&&!response.already){clearTimeout(toastTimer);$('toast').hidden=true;requestAnimationFrame(()=>{$('toast').hidden=false;toastTimer=setTimeout(()=>$('toast').hidden=true,6000);});}}catch(error){$('feedback').textContent=error.message;$('feedback').className='error';}finally{busy=false;$('submit').disabled=false;}};
async function operation(action,question){if(busy||!confirm(question))return;busy=true;$('restore').disabled=true;$('clear-progress').disabled=true;try{const response=await api(action,{program:active,confirm:true});if(action==='restore'){const t=terminals.get(active);if(t){t.term.dispose();t.host.remove();terminals.delete(active);}try{sessionStorage.removeItem('crack4fun:terminal:'+active);}catch(_){}state.ready[active]=true;clearTimeout(pollTimer);await connect();}else state.completed=response.completed;render();notice(response.message||'Progress for this program cleared.');}catch(error){notice(error.message,true);}finally{busy=false;$('restore').disabled=false;$('clear-progress').disabled=false;}}
$('restore').onclick=()=>operation('restore','Restore this program’s original scenario files and restart its terminals? Working notes in /work will be removed. Saved completion will remain.');
$('clear-progress').onclick=()=>operation('clear-progress','Clear completed flags for this program? Files and terminals will stay unchanged.');
$('prepare').onclick=async()=>{if(busy)return;busy=true;$('prepare').disabled=true;try{await api('prepare',{program:active});state.ready[active]=true;render();await connect();}catch(error){notice(error.message,true);}finally{busy=false;$('prepare').disabled=false;}};
$('menu').onclick=()=>document.querySelector('.shell').classList.toggle('nav-open');
async function boot(){try{state=await api('state');active=state.active;render();await connect();if(!state.tutorial_seen)startTutorial();}catch(error){notice(error.message,true);}}
setInterval(async()=>{if(!state||busy||document.hidden)return;try{const next=await api('state');const wasReady=state.ready[active];state.ready=next.ready;state.errors=next.errors;if(!wasReady&&state.ready[active]){render();connect();}}catch(_){}},3000);


// One guided introduction per saved learner session, replayable from the toolbar.
const tourSteps=[
  {label:'Welcome',title:'Learn to follow the clues.',text:'A capture-the-flag challenge is a small investigation. Explore a prepared environment, find a hidden piece of text, and submit it as proof of what you discovered. Take your time. Everything here is part of a practice scenario.'},
  {label:'The basics',title:'What does a flag look like?',text:'A flag is a piece of text inside curly braces. Copy the whole thing, including the braces, exactly as you find it. Each task has its own flag. The example below is for practice only.',code:'{example_training_flag}',caption:'This illustrates the format. It is not an answer to a challenge.'},
  {label:'The basics',title:'Meet the terminal.',text:'The terminal lets you talk to Linux by typing commands. Click inside it, type a command, and press Enter. Start with these three: find your current directory, list its files, then read a file. Use the actual filename you discover.',code:'pwd\nls -la\ncat filename.txt',caption:'pwd: where am I?   ls -la: what is here, including hidden files?   cat: read a file. Use ↑ to recall a command and Ctrl+C to stop one.'},
  {label:'Your course',title:'Four ways to investigate.',text:'Each program tells its own connected story. Start with Filesystem if the terminal is new to you. You can switch programs at any time; progress stays saved.',topics:true},
  {label:'Your workspace',title:'Choose a program.',text:'The sidebar switches between Filesystem, Forensics, Network Analysis, and Web/API. Each program has its own environment and terminal. The small count shows how many flags you have found.',target:'.sidebar'},
  {label:'Your workspace',title:'Follow one task at a time.',text:'Choose a challenge here, then read its goal and “Start here” location below. Tasks become more involved as you go. Switching tasks changes the instructions, keeping your terminal and files in place.',target:'.mission'},
  {label:'Your workspace',title:'A nudge when you need it.',text:'Open “Need a hint?” and reveal one hint at a time. Try the idea before asking for another. In Forensics and Network Analysis, “Download evidence” also lets you open files in your own desktop tools.',target:'#hint'},
  {label:'Your workspace',title:'Explore in your terminal.',text:'This is a real shell in this program’s container. Commands run as apprentice. Click the dark area before typing. “Connected” means the terminal is ready; first startup may briefly say “Preparing…” while the scenario files are created. Web/API also offers a Portal tab for its website.',target:'.lab'},
  {label:'Your workspace',title:'Submit what you found.',text:'Paste the complete flag here and select “Submit flag”. A correct answer updates your progress immediately. An incorrect answer is an invitation to check the clue, the selected task, and what you copied.',target:'#flag-form'},
  {label:'Your workspace',title:'Your progress stays with you.',text:'This bar tracks the current program. Accepted flags save automatically, including after a refresh or restart. You can return to completed tasks to practise again.',target:'.progress'},
  {label:'A fresh start',title:'Two different kinds of reset.',text:'“Restore files” puts this program’s scenario back and removes scratch work, while keeping completed flags. “Clear progress” removes its completion history, keeping files. Both ask first. You can replay this guide anytime with Tutorial.',target:'.toolbar-actions'}
];
let tourStep=0,tourOriginal=null,tourSaving=false,tourAnimations=[];
const tourMotion=matchMedia('(prefers-reduced-motion: reduce)');
function tourTarget(){return document.querySelector(tourSteps[tourStep].target||'#not-a-tour-target');}
function positionTour(){
  if(!$('tour').open)return;
  const card=$('tour-card'),target=tourTarget(),pad=16,gap=16;
  const width=card.offsetWidth,height=card.offsetHeight;
  const clamp=(value,max)=>Math.max(pad,Math.min(value,Math.max(pad,max)));
  let x=(innerWidth-width)/2,y=(innerHeight-height)/2;
  const spot=$('tour-spotlight');spot.hidden=!target;
  if(target){
    const r=target.getBoundingClientRect();
    Object.assign(spot.style,{left:(r.left-4)+'px',top:(r.top-4)+'px',width:(r.width+8)+'px',height:(r.height+8)+'px'});
    const cy=clamp(r.top+(r.height-height)/2,innerHeight-height-pad);
    const cx=clamp(r.left+(r.width-width)/2,innerWidth-width-pad);
    const options=[{x:r.right+gap,y:cy},{x:r.left-width-gap,y:cy},{x:cx,y:r.bottom+gap},{x:cx,y:r.top-height-gap}];
    const point=options.find(p=>p.x>=pad&&p.y>=pad&&p.x+width<=innerWidth-pad&&p.y+height<=innerHeight-pad);
    if(point){x=point.x;y=point.y;}else{x=cx;y=tourSteps[tourStep].target==='.sidebar'?innerHeight-height-pad:(r.top>innerHeight-r.bottom?pad:innerHeight-height-pad);}
  }
  card.style.left=clamp(x,innerWidth-width-pad)+'px';card.style.top=clamp(y,innerHeight-height-pad)+'px';
}
function renderTour(){
  const card=$('tour-card'),previous=card.getBoundingClientRect(),step=tourSteps[tourStep];
  tourAnimations.forEach(a=>a.cancel());tourAnimations=[];
  document.querySelector('.shell').classList.toggle('nav-open',!!step.target&&step.target==='.sidebar'&&innerWidth<=800);
  $('tour-count').textContent=`${tourStep+1} of ${tourSteps.length}`;
  $('tour-label').textContent=step.label;$('tour-title').textContent=step.title;$('tour-text').textContent=step.text;
  $('tour-example').hidden=!step.code;$('tour-code').textContent=step.code||'';$('tour-caption').textContent=step.caption||'';
  $('tour-topics').hidden=!step.topics;
  $('tour-topics').replaceChildren(...(step.topics?[
    ['Filesystem','Explore files, permissions, and a forgotten handover.'],['Forensics','Decode bytes, inspect evidence, and recover a weak password.'],['Network Analysis','Follow conversations in a prepared packet capture.'],['Web/API','Inspect a website and make requests to its API.']
  ]:[]).map(([title,text])=>{const topic=node('div');topic.append(node('strong',title),node('p',text));return topic;}));
  $('tour-back').disabled=tourStep===0;$('tour-next').textContent=tourStep===tourSteps.length-1?'Start exploring':'Next';$('tour-error').textContent='';
  // Reveal the hint control for its guided stop without consuming a hint.
  const hintDetails=$('hint').closest('details');hintDetails.open=step.target==='#hint'?true:tourOriginal.hintsOpen;
  const target=tourTarget();if(target)target.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});
  positionTour();$('tour-content').scrollTop=0;
  if(!tourMotion.matches&&previous.width){
    const next=card.getBoundingClientRect();
    tourAnimations.push(card.animate([{transform:`translate(${previous.left-next.left}px,${previous.top-next.top}px) scale(${previous.width/next.width},${previous.height/next.height})`},{transform:'none'}],{duration:260,easing:'cubic-bezier(.2,.7,.2,1)'}));
    tourAnimations.push($('tour-content').animate([{opacity:.25,transform:'translateY(4px)'},{opacity:1,transform:'none'}],{duration:200}));
  }
}
function startTutorial(){
  if(!state||busy||$('tour').open)return;
  tourOriginal={x:scrollX,y:scrollY,nav:document.querySelector('.shell').classList.contains('nav-open'),hintsOpen:$('hint').closest('details').open,focus:document.activeElement};
  tourStep=0;$('tour').showModal();renderTour();$('tour-next').focus();
}
async function finishTutorial(){
  if(tourSaving)return;tourSaving=true;
  for(const id of ['tour-back','tour-next','tour-skip'])$(id).disabled=true;
  try{
    await api('tutorial',{});state.tutorial_seen=true;
    $('tour').close();tourAnimations.forEach(a=>a.cancel());
    document.querySelector('.shell').classList.toggle('nav-open',tourOriginal.nav);
    $('hint').closest('details').open=tourOriginal.hintsOpen;
    scrollTo({left:tourOriginal.x,top:tourOriginal.y,behavior:'instant'});
    (tourOriginal.focus?.isConnected?tourOriginal.focus:$('tutorial')).focus({preventScroll:true});
  }catch(error){$('tour-error').textContent='Could not save tutorial completion. '+error.message;}
  finally{tourSaving=false;for(const id of ['tour-next','tour-skip'])$(id).disabled=false;$('tour-back').disabled=tourStep===0;}
}
$('tutorial').onclick=startTutorial;
$('tour-next').onclick=()=>{if(tourSaving)return;if(tourStep===tourSteps.length-1)finishTutorial();else{tourStep++;renderTour();}};
$('tour-back').onclick=()=>{if(!tourSaving&&tourStep>0){tourStep--;renderTour();}};
$('tour-skip').onclick=finishTutorial;
$('tour').addEventListener('cancel',event=>{event.preventDefault();finishTutorial();});
window.addEventListener('resize',positionTour);window.addEventListener('scroll',positionTour,true);
new ResizeObserver(positionTour).observe($('tour-card'));
tourMotion.addEventListener('change',()=>{if(tourMotion.matches)tourAnimations.forEach(a=>a.cancel());});
boot();
