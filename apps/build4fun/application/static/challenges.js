'use strict';
const byId = id => document.getElementById(id);
let data, busy = false, signature = '';
function node(tag, text, className) {
  const result = document.createElement(tag); result.textContent = text;
  if (className) result.className = className;
  return result;
}
function passed(project, challenge) {
  const checks = project.checks[challenge.id];
  return !project.error && checks?.length === challenge.checks.length && checks.every(Boolean);
}
function render() {
  const selected = data.projects.find(p => p.id === byId('project').value);
  const count = data.challenges.filter(c => data.projects.some(p => passed(p, c))).length;
  byId('collection').textContent = data.challenges.length > 0 && count === data.challenges.length ? `Collection complete — all ${data.challenges.length} challenges!` : `${count} / ${data.challenges.length} challenges collected`;
  byId('progress').max = data.challenges.length; byId('progress').value = count;
  byId('status').textContent = !selected ? 'Create and save a project in the workspace to begin.' : selected.error ? `Fix this project’s validation issue before checking: ${selected.error}` : 'Checking saved configuration automatically. Last successful refresh: ' + new Date().toLocaleTimeString();
  const key = JSON.stringify([data, selected?.id]);
  if (key === signature) return;
  signature = key;
  byId('challenges').replaceChildren();
  data.challenges.forEach((challenge, index) => {
    const collected = data.projects.filter(p => passed(p, challenge));
    const card = node('article', '', 'challenge-card' + (collected.length ? ' complete' : ''));
    card.append(node('p', `${challenge.level} · Challenge ${index + 1}`, 'eyebrow'), node('h2', challenge.title));
    card.append(node('p', collected.length ? 'Collected in: ' + collected.map(p => p.name).join(', ') : 'Not collected yet', collected.length ? 'badge' : ''));
    card.append(node('p', challenge.goal));
    const steps = document.createElement('ol'); challenge.steps.forEach(s => steps.append(node('li', s))); card.append(steps);
    card.append(node('h3', 'Automatic checks · selected project'));
    const checks = node('ul', '', 'checklist');
    challenge.checks.forEach((label, i) => {
      const ok = !selected?.error && selected?.checks[challenge.id]?.[i];
      checks.append(node('li', `${ok ? '✓ Passed' : '○ Pending'} — ${label}`, ok ? 'passed' : ''));
    });
    card.append(checks, node('h3', 'Explain it'), node('p', challenge.question), node('h3', 'Try it for real'), node('p', challenge.experiment));
    const link = node('a', 'Read Markdown lesson ↗'); link.href = `/docs/challenges/${challenge.id}.md`; card.append(link);
    byId('challenges').append(card);
  });
}
async function refresh() {
  if (busy) return;
  busy = true; byId('refresh').disabled = true;
  try {
    const response = await fetch('/api/challenges');
    if (!response.ok) throw new Error('Could not load challenges.');
    const next = await response.json();
    const select = byId('project'), current = select.value;
    if (JSON.stringify(data?.projects.map(p => [p.id,p.name])) !== JSON.stringify(next.projects.map(p => [p.id,p.name]))) {
      select.replaceChildren(...next.projects.map(p => {const option = node('option', p.name); option.value = p.id; return option;}));
      if (next.projects.some(p => p.id === current)) select.value = current;
    }
    data = next; render();
  } catch (error) {
    byId('status').textContent = 'Checks unavailable — displayed results may be stale. ' + error.message;
  } finally { busy = false; byId('refresh').disabled = false; }
}
byId('project').addEventListener('change', render);
byId('refresh').addEventListener('click', refresh);
document.addEventListener('visibilitychange', () => {if (!document.hidden) refresh();});
setInterval(() => {if (!document.hidden) refresh();}, 5000);
refresh();
