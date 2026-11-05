const $ = id => document.getElementById(id);
$('greet').addEventListener('click', () => $('message').textContent = 'Hello, apprentice!');
$('theme-toggle').addEventListener('click', () => document.body.classList.toggle('dark'));
async function read(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error('Request failed');
  return response.json();
}
let pending = false;
async function refresh() {
  if (pending) return;
  pending = true;
  $('status').textContent = 'Loading…';
  try {
    const [user, host, ip, metrics] = await Promise.all(['/api/username/','/api/hostname/','/api/ip','/api/metrics'].map(read));
    $('username').textContent = user.username;
    $('hostname').textContent = host.hostname;
    $('addresses').textContent = ip.addresses.join(', ');
    for (const [id, key] of Object.entries({'cpu':'cpu_percent','memory':'memory_used_bytes','memory-limit':'memory_limit_bytes','uptime':'uptime_seconds'})) {
      $(id).textContent = metrics[key] === null ? 'N/A' : String(metrics[key]);
    }
    $('status').textContent = 'Up to date';
  } catch (error) { $('status').textContent = 'Error: could not load server information.'; }
  finally { pending = false; }
}
$('refresh').addEventListener('click', refresh);
refresh();
setInterval(refresh, 5000);
