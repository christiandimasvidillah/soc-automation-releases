const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[character]));

async function fetchJson(url) {
  const response = await fetch(url, {
    method: 'GET',
    headers: {'Accept': 'application/json'},
    cache: 'no-store'
  });
  if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}`);
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) throw new Error(`Invalid content type: ${contentType || 'missing'}`);
  try { return await response.json(); }
  catch (error) { throw new Error(`Invalid JSON response: ${error.message}`); }
}

const positive = new Set(['RUNNING','AVAILABLE','ACTIVE','ALIVE','HEALTHY','LISTENING','OK']);
const warning = new Set(['READY','STANDBY','SHADOW','APPROVAL','READ-ONLY']);
const impact = new Set(['GLOBAL','LIMITED']);
const negative = new Set(['UNKNOWN','INACTIVE','DISABLED','STOPPED','DEAD','NOT_RUNNING','NOT-RUNNING','UNAVAILABLE','FAILED','ERROR','UNHEALTHY','CHECK_REQUIRED']);
function statusClass(value) {
  const normalized = String(value || 'UNKNOWN').toUpperCase();
  if (positive.has(normalized)) return 'status-ok';
  if (warning.has(normalized)) return 'status-warn';
  if (impact.has(normalized)) return 'status-impact';
  if (negative.has(normalized)) return 'status-bad';
  return 'status-neutral';
}
function serviceCardClass(service) {
  const state = String(service.state || 'UNKNOWN').toUpperCase();
  const health = String(service.health || 'UNKNOWN').toUpperCase();
  if (negative.has(state) || negative.has(health)) return 'service-bad';
  if (positive.has(state) && positive.has(health)) return 'service-ok';
  if (warning.has(state) || warning.has(health)) return 'service-warn';
  return 'service-neutral';
}
function renderServices(payload) {
  const element = $('#serviceHealth');
  if (!element) return;
  const rows = Array.isArray(payload) ? payload : (Array.isArray(payload?.services) ? payload.services : []);
  element.innerHTML = '';
  if (!rows.length) {
    element.innerHTML = '<div class="service-empty"><strong>Service data unavailable</strong><span>The viewer received no service rows. Check /api/services or restart the viewer.</span></div>';
    return;
  }
  for (const service of rows) {
    const state = String(service.state || 'UNKNOWN').toUpperCase();
    const health = String(service.health || 'UNKNOWN').toUpperCase();
    const mode = String(service.mode || '-').toUpperCase();
    const card = document.createElement('article');
    card.className = `service-card ${serviceCardClass(service)}`;
    card.innerHTML = `
      <div class="service-title"><strong>${esc(service.name || service.id || 'Unknown service')}</strong><span class="service-dot"></span></div>
      <div class="service-row"><span>Mode</span><b class="${statusClass(mode)}">${esc(mode)}</b></div>
      <div class="service-row"><span>State</span><b class="${statusClass(state)}">${esc(state)}</b></div>
      <div class="service-row"><span>PID</span><b>${esc(service.pid || '-')}</b></div>
      <div class="service-row"><span>Health</span><b class="${statusClass(health)}">${esc(health)}</b></div>`;
    element.appendChild(card);
  }
}
async function refreshServices() {
  const element = $('#serviceHealth');
  try { renderServices(await fetchJson(`/api/services?ts=${Date.now()}`)); }
  catch (error) {
    console.error('service health refresh failed', error);
    if (element) element.innerHTML = `<div class="service-error"><strong>Service health unavailable</strong><span>${esc(error.message || error)}</span></div>`;
  }
}

let paused = false, selected = null, lastTimeline = {};
function age(epoch) { const seconds=Math.max(0,Math.floor(Date.now()/1000-Number(epoch||0))); return seconds<60?`${seconds}s`:seconds<3600?`${Math.floor(seconds/60)}m`:`${Math.floor(seconds/3600)}h`; }
function cls(status) { return ['PASS','COMPLETED'].includes(status)?'ok':['FAILED','BLOCKED'].includes(status)?'bad':'warn'; }
function jira(event) { return event.jira_status || event.details?.jira_status || '-'; }
async function status() {
  try {
    const data=await fetchJson(`/api/status?ts=${Date.now()}`);
    $('#release').textContent=data.version||data.release||'-'; $('#slot').textContent=data.active_slot||'-'; $('#master').textContent=data.master?.status||data.master_status||'unknown';
    const workers=data.workers||{};
    $('#workers').innerHTML=Object.entries(workers).map(([name,value])=>`<div class="worker"><div><span class="dot"></span><strong>${esc(name)}</strong></div><div class="row"><span class="muted">Status</span><b class="${statusClass(value.status)}">${esc(value.status||'unknown')}</b></div><div class="row"><span class="muted">PID</span><b>${esc(value.pid||'-')}</b></div></div>`).join('')||'<div class="muted">No worker status.</div>';
    $('#stamp').textContent=`Updated ${new Date().toLocaleTimeString()}`;
  } catch (error) { $('#stamp').textContent=`Status unavailable: ${error.message}`; }
}
function renderTrace(){const list=lastTimeline[selected]||[];$('#trace-title').textContent=selected?`Timeline - ${selected}`:'Timeline';$('#timeline').innerHTML=list.length?list.map(event=>`<div class="trace"><span>${esc(new Date(event.epoch*1000).toLocaleTimeString())}</span><b class="${cls(event.status)}">${esc(event.stage)}</b><span>${esc(event.status)}</span><span class="jira">${esc(jira(event))}</span></div>`).join(''):'<div class="muted">No timeline available.</div>';}
async function tickets(){if(paused)return;try{const data=await fetchJson(`/api/tickets?ts=${Date.now()}`);const rows=data.tickets||[];lastTimeline=data.timeline||{};$('#live-count').textContent=rows.filter(item=>['RUNNING','WAITING','RETRY','BLOCKED'].includes(item.status)).length;$('#tickets').innerHTML=rows.length?rows.map(event=>`<tr data-ticket="${esc(event.ticket_key)}"><td><b>${esc(event.ticket_key)}</b></td><td>${esc(event.worker)}</td><td>${esc(event.stage)}</td><td class="${cls(event.status)}">${esc(event.status)}</td><td class="jira">${esc(jira(event))}</td><td>${age(event.epoch)}</td></tr>`).join(''):'<tr><td colspan="6" class="muted">Waiting for ticket events...</td></tr>';document.querySelectorAll('#tickets tr[data-ticket]').forEach(row=>row.onclick=()=>{selected=row.dataset.ticket;renderTrace();});renderTrace();$('#ticket-stamp').textContent=`Updated ${new Date().toLocaleTimeString()}`;}catch(error){$('#ticket-stamp').textContent=`Live feed unavailable: ${error.message}`;}}
async function history(){try{const data=await fetchJson(`/api/ticket-history?ts=${Date.now()}`);const rows=data.tickets||[];$('#history').innerHTML=rows.length?rows.map(event=>`<tr><td><b>${esc(event.ticket_key)}</b></td><td>${esc(event.worker)}</td><td>${esc(event.stage)}</td><td class="${cls(event.status)}">${esc(event.status)}</td><td class="jira">${esc(jira(event))}</td><td>${esc(new Date(event.last_epoch*1000).toLocaleString())}</td><td>${esc(event.events)}</td></tr>`).join(''):'<tr><td colspan="7" class="muted">No retained ticket history.</td></tr>';$('#history-policy').textContent=`Completed ${data.retention?.completed_days||7}d | Failed ${data.retention?.failed_days||30}d`;}catch(error){$('#history').innerHTML=`<tr><td colspan="7" class="bad">History unavailable: ${esc(error.message)}</td></tr>`;}}

function featureLabel(key){return String(key).replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());}
async function refreshFeatures(){
 try{
  const data=await fetchJson(`/api/features?ts=${Date.now()}`);
  $('#featureProfile').textContent=`Profile ${data.profile} | Revision ${data.revision}`;
  const rows=Object.entries(data.effective||{});
  $('#featureHealth').innerHTML=rows.map(([key,value])=>`<div class="feature-row"><span>${esc(featureLabel(key))}</span><b class="${value.effective?'status-ok':'status-bad'}">${value.effective?'ON':'OFF'}</b><small>${esc(value.reason||'effective')}</small></div>`).join('');
 }catch(error){$('#featureHealth').innerHTML=`<div class="service-error">Feature status unavailable: ${esc(error.message)}</div>`;}
}
async function refreshAI(){
 try{
  const data=await fetchJson(`/api/ai-health?ts=${Date.now()}`); const local=data.local_ai||{},gemini=data.gemini||{};
  $('#aiHealth').innerHTML=`<article class="service-card ${local.mode==='ENABLED'?'service-ok':'service-bad'}"><strong>Local AI</strong><div class="service-row"><span>Provider</span><b>${esc(local.provider||'-')}</b></div><div class="service-row"><span>Model</span><b>${esc(local.model||'-')}</b></div><div class="service-row"><span>Mode</span><b class="${statusClass(local.mode)}">${esc(local.mode||'-')}</b></div><div class="service-row"><span>Reachable</span><b class="${local.reachable?'status-ok':'status-bad'}">${local.reachable?'YES':'NO'}</b></div></article><article class="service-card ${gemini.mode==='ENABLED'?'service-ok':'service-bad'}"><strong>Gemini</strong><div class="service-row"><span>Provider</span><b>${esc(gemini.provider||'-')}</b></div><div class="service-row"><span>Preferred model</span><b>${esc(gemini.preferred_model||'-')}</b></div><div class="service-row"><span>Mode</span><b class="${statusClass(gemini.mode)}">${esc(gemini.mode||'-')}</b></div><div class="service-row"><span>Credential</span><b class="${gemini.credential_configured?'status-ok':'status-bad'}">${gemini.credential_configured?'CONFIGURED':'MISSING'}</b></div></article>`;
 }catch(error){$('#aiHealth').innerHTML=`<div class="service-error">AI health unavailable: ${esc(error.message)}</div>`;}
}
$('#pause').onclick=event=>{event.preventDefault();event.stopPropagation();paused=!paused;$('#pause').textContent=paused?'Resume':'Pause';if(!paused)tickets();};
refreshServices();refreshFeatures();refreshAI();status();tickets();history();setInterval(status,5000);setInterval(refreshServices,5000);setInterval(refreshFeatures,5000);setInterval(refreshAI,5000);setInterval(tickets,1000);setInterval(history,5000);
