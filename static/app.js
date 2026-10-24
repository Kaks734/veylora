'use strict';const $=id=>document.getElementById(id);let state={devices:[],labels:{}},token='',demo=false;
function message(t){$('notice').textContent=t}
async function post(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json','X-NetPulse-Token':token},body:JSON.stringify(body)});const j=await r.json();if(!r.ok){const error=Error(j.error);error.details=j;error.httpStatus=r.status;throw error;}return j}
function deviceName(mac,device){return state.labels?.[mac]||device?.hostname||(device?.role==='Router'?'Router':'Unknown device')}
function render(){renderMonitoring();const ds=state.devices||[];$('total').textContent=ds.length;$('online').textContent=ds.filter(d=>d.status==='Responding').length;$('mode').textContent=demo?'DEMO':'LOCAL';$('scan').disabled=!!state.scanning;$('scan').textContent=state.scanning?'Scanning…':'Scan my network';$('list').replaceChildren();const q=$('search').value.toLowerCase();ds.filter(d=>`${d.ip} ${d.mac} ${state.labels[d.mac]||''} ${d.hostname||''}`.toLowerCase().includes(q)).forEach(d=>{const row=document.createElement('div');row.className='device';const edit=document.createElement('button');edit.textContent='Rename';edit.onclick=async()=>{const name=prompt('Label (maximum 80 characters)',state.labels[d.mac]||'');if(name===null)return;if(name.length>80)return message('Maximum 80 characters.');try{if(demo){state.labels[d.mac]=name;render()}else{await post('/api/label',{mac:d.mac,name});await refresh()}}catch(e){message(e.message)}};row.append(edit);for(const [text,cls] of [[deviceName(d.mac,d),'name'],[d.ip,''],[d.mac,''],[d.status,d.status==='Responding'?'status':'cached'],[d.last_seen?'Last seen '+new Date(d.last_seen*1000).toLocaleTimeString():'Not confirmed responding','last-seen']]){const p=document.createElement('p');p.textContent=text;p.className=cls;if(text===d.mac){p.classList.add('mac-line');p.append(copyButton(d.mac))}row.append(p)}const use=document.createElement('button');use.className='use-device';use.textContent='Use this device';use.onclick=()=>{if(demo)return toast('Exit demo to select a real device.');$('targetMAC').value=d.mac;$('routerPanel').scrollIntoView({behavior:reduced?'instant':'smooth',block:'start'});$('targetMAC').focus();toast('Device selected. Verify its Wi-Fi SSID before changing access.');};row.append(use);$('list').append(row)});if(!$('list').children.length){const p=document.createElement('p');p.textContent='No devices to show. Scan your network or try demo.';$('list').append(p)}if(typeof renderBlocked==='function')renderBlocked()}
async function refresh(){if(demo)return;try{const r=await fetch('/api/state');if(!r.ok)throw Error();state=await r.json();token=state.token;render();message(state.error||(state.scanning?'Scanning your selected local subnet…':state.updated?`Updated ${new Date(state.updated*1000).toLocaleTimeString()} · ${state.interface.name}. Cached entries are unconfirmed.`:'Ready. Choose your network interface and scan.'))}catch(e){message('Cannot reach Veylora. Check that app.py is running.')}}
$('demo').onclick=async()=>{demo=!demo;$('demo').textContent=demo?'Exit demo':'Try demo';if(demo){state={labels:{},devices:Array.from({length:7},(_,i)=>({ip:`192.168.1.${i+10}`,mac:`02:00:00:00:00:0${i}`,status:i<5?'Responding':'Cached / unconfirmed',role:i===0?'Router':'Device',hostname:['Demo gateway','Demo laptop','Demo phone','Demo TV','Demo speaker','Demo tablet','Demo guest'][i]}))};render();message('DEMO — fictional sample devices. No router changes are made.')}else await refresh()};$('scan').onclick=async()=>{try{if(demo){demo=false;$('demo').textContent='Try demo';await refresh()}await post('/api/scan',{interface:$('interface').value?Number($('interface').value):null});await setMonitor(true);await refresh()}catch(e){message(e.message)}};$('search').oninput=render;
const c=$('radar'),ctx=c.getContext('2d'),reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;function draw(t){const x=350,y=300,r=255;ctx.clearRect(0,0,700,600);ctx.strokeStyle='#294c54';for(let i=1;i<=4;i++){ctx.beginPath();ctx.arc(x,y,r*i/4,0,Math.PI*2);ctx.stroke()}for(let i=0;i<12;i++){const a=i*Math.PI/6;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.cos(a)*r,y+Math.sin(a)*r);ctx.stroke()}const sweep=reduced?0:t/1800;for(let i=0;i<50;i++){const a=sweep-i*.013;ctx.strokeStyle=`rgba(100,245,200,${.3*(1-i/50)})`;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.cos(a)*r,y+Math.sin(a)*r);ctx.stroke()}ctx.fillStyle='#79f4ce';ctx.beginPath();ctx.arc(x,y,7,0,Math.PI*2);ctx.fill();(state.devices||[]).filter(d=>demo||d.present||d.status==='Responding').forEach((d,i)=>{let hash=0;for(const char of d.mac)hash=(hash*31+char.charCodeAt(0))>>>0;const a=(hash%360)*Math.PI/180,dist=80+(hash%160),dx=x+Math.cos(a)*dist,dy=y+Math.sin(a)*dist;ctx.fillStyle=d.status==='Responding'?'#79f4ce':'#e5bb75';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=14;ctx.beginPath();ctx.arc(dx,dy,6,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.font='12px Segoe UI';ctx.fillText((deviceName(d.mac,d)).slice(0,22),Math.min(dx+10,530),dy-12)});requestAnimationFrame(draw)}requestAnimationFrame(draw);fetch('/api/interfaces').then(r=>r.json()).then(j=>{for(const i of j.interfaces){const o=document.createElement('option');o.value=i.index;o.textContent=`${i.name} · ${i.ip}`;$('interface').append(o)}}).catch(()=>{});refresh().then(()=>restoreRouter());setInterval(refresh,2000);


let routerBusy=false,routerConnected=false,routerVerified=false,routerState=null,toastTimer,lastRuleCheck=0;
function toast(text){$('toast').textContent=text;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),3000)}
function copyButton(mac){const button=document.createElement('button');button.type='button';button.className='copy-mac';button.textContent='Copy';button.setAttribute('aria-label','Copy MAC address '+mac);button.onclick=async()=>{try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(mac);else{const field=document.createElement('textarea');field.value=mac;document.body.append(field);field.select();const ok=document.execCommand('copy');field.remove();if(!ok)throw Error()}button.textContent='Copied';toast('MAC address copied');setTimeout(()=>button.textContent='Copy',1600)}catch(e){toast('Could not access clipboard. Select the MAC and press Ctrl+C.')}};return button}
function normalizeMAC(value){return value.trim().toLowerCase().replaceAll('-',':')}
function updateRouterControls(){const compatible=$('routerProfile').value==='hg8546m';const editable=compatible&&routerConnected&&routerVerified&&routerState?.enabled&&routerState?.mode==='blacklist'&&!demo&&!routerBusy;for(const id of ['blockDevice','unblockDevice'])$(id).disabled=!editable;for(const el of document.querySelectorAll('.inline-unblock'))el.disabled=!editable;for(const id of ['routerRefresh','routerDisconnect'])$(id).disabled=!routerConnected||routerBusy;$('connectRouter').disabled=routerBusy||demo||!compatible;$('connectRouter').textContent=routerBusy?'Working…':routerConnected?'Reconnect router':'Connect router';$('connectionBadge').className='connection-badge'+(routerBusy?' pending':routerConnected?' connected':'');$('connectionBadge').textContent=routerBusy?'◌ Working…':routerConnected?(routerVerified?'● Connected':'◌ Checking connection'):'● Not connected'}
function showRules(s){routerVerified=!s.disconnected;lastRuleCheck=Date.now();routerConnected=!s.disconnected;routerState=s.disconnected?null:s;if(s.router_ip){$('routerIP').value=s.router_ip;$('routerLink').href='http://'+s.router_ip;}if(s.protected_mac)$('protectedMAC').value=s.protected_mac;$('routerRules').replaceChildren();$('ruleCount').textContent=s.rules?.length||0;$('filterSummary').textContent=s.disconnected?'Disconnected':`${s.enabled?'Filtering enabled':'Filtering disabled'} · ${s.mode==='blacklist'?'Blacklist':'Allowlist'} · checked ${new Date().toLocaleTimeString()}`;$('routerMessage').className='router-feedback'+(s.disconnected?'':' success');$('routerMessage').textContent=s.disconnected?'Disconnected locally. The router session may remain valid until it expires.':!s.enabled?'Connected. Filtering is disabled. Review existing rules in the router before enabling it, then refresh here.':s.mode!=='blacklist'?'Connected in allowlist mode. Manage allowlists in the router dashboard.':'Connected. Blacklist controls are ready. Saved rules are verified after each change.';for(const r of s.rules||[]){const row=document.createElement('div');row.className='rule-row';const ssid=document.createElement('span');ssid.className='ssid-chip';ssid.textContent=r.ssid.replace('-',' ');const mac=document.createElement('code');mac.textContent=r.mac;const select=document.createElement('button');select.type='button';select.className='quiet';select.textContent='Select';select.onclick=()=>{$('targetMAC').value=r.mac;$('targetSSID').value=r.ssid;$('targetMAC').focus();toast('Saved rule selected')};row.append(ssid,mac,copyButton(r.mac),select);$('routerRules').append(row)}if(!$('routerRules').children.length){const p=document.createElement('p');p.className='rules-empty';p.textContent=s.disconnected?'Connect to load saved access rules.':'No saved rules on this router.';$('routerRules').append(p)}renderBlocked();updateRouterControls()}
async function routerCall(path,body,{silent=false}={}){
 if(demo){if(!silent)toast('Exit demo before using router controls.');return}
 if(routerBusy)return;if(path.endsWith('/connect')&&$('routerProfile').value!=='hg8546m'){toast('This router profile supports discovery only.');return}routerBusy=true;updateRouterControls();
 if(!silent){$('routerMessage').className='router-feedback';$('routerMessage').textContent=path.endsWith('connect')?'Connecting to your router…':'Reading and verifying router settings…'}
 try{
  const result=await post(path,body);showRules(result);
  if(path.endsWith('/connect')&&!result.disconnected)await setMonitor(true);
  if(path.endsWith('/change')){toast('Saved rule verified. Session retained.');await requestScanSoon()}
 }catch(e){
  // Validation, propagation delays and temporary read failures do not log the user out.
  if(e.details?.session_active===false||e.httpStatus===401){routerConnected=false;routerState=null}
  routerVerified=false;
  if(routerConnected&&path.endsWith('/change')){
   try{const recovered=await post('/api/router/status',{});showRules(recovered)}catch(ignored){}
  }
  $('routerMessage').className='router-feedback error';
  $('routerMessage').textContent=e.message+(routerConnected?' Your session is retained; refresh rules to check the current configuration.':'');
  if(!routerVerified)$('filterSummary').textContent='Last displayed rules may be stale · checking again automatically';
  renderBlocked();
 }finally{routerBusy=false;updateRouterControls()}
}
async function restoreRouter(){await routerCall('/api/router/status',{}, {silent:true})}
setInterval(()=>{if(routerConnected&&!routerBusy&&!demo&&Date.now()-lastRuleCheck>=30000){lastRuleCheck=Date.now();routerCall('/api/router/status',{}, {silent:true})}},5000);
$('routerForm').onsubmit=async e=>{e.preventDefault();const credentials={address:$('routerIP').value.trim(),username:$('routerUser').value,password:$('routerPassword').value,protected:normalizeMAC($('protectedMAC').value)};if(!/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/.test(credentials.protected))return toast('Enter a valid protected Wi-Fi MAC.');if(/^192\.168\.\d{1,3}\.\d{1,3}$/.test(credentials.address))$('routerLink').href='http://'+credentials.address;$('routerPassword').value='';await routerCall('/api/router/connect',credentials);credentials.password=''};
$('showPassword').onclick=()=>{const shown=$('routerPassword').type==='password';$('routerPassword').type=shown?'text':'password';$('showPassword').textContent=shown?'Hide':'Show';$('showPassword').setAttribute('aria-pressed',String(shown));$('showPassword').setAttribute('aria-label',shown?'Hide password':'Show password')};
$('pasteMAC').onclick=async()=>{try{$('targetMAC').value=normalizeMAC(await navigator.clipboard.readText());$('targetMAC').focus();toast('MAC pasted')}catch(e){$('targetMAC').focus();toast('Press Ctrl+V in the Device MAC field to paste.')}};
$('routerRefresh').onclick=()=>routerCall('/api/router/status',{});$('routerDisconnect').onclick=()=>routerCall('/api/router/disconnect',{});for(const action of ['block','unblock'])$(action+'Device').onclick=()=>{const mac=normalizeMAC($('targetMAC').value),ssid=$('targetSSID').value;if(!/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/.test(mac))return toast('Enter a valid device MAC address.');if(mac===normalizeMAC($('protectedMAC').value))return toast('This is your protected Wi-Fi adapter.');if(confirm(`${action==='block'?'Block':'Unblock'} access for ${mac} on ${ssid}?`))routerCall('/api/router/change',{action,mac,ssid})};
const originalDemoClick=$('demo').onclick;$('demo').onclick=async()=>{await originalDemoClick();updateRouterControls()};
updateRouterControls();

function renderBlocked(){
 const list=$('blockedList');if(!list)return;list.replaceChildren();
 const active=!demo&&routerConnected&&routerVerified&&routerState?.enabled&&routerState?.mode==='blacklist';
 const rules=!demo&&routerState?.mode==='blacklist'?routerState.rules||[]:[];
 $('blockedCount').textContent=active?rules.length:0;
 $('blockedSummary').textContent=demo?'Demo mode — live router rules hidden.':!routerConnected?'Router connection unverified. Reconnect to load current blocks.':!routerState?.enabled?'Filtering is disabled. Saved rules are inactive.':routerState.mode!=='blacklist'?'Allowlist mode is active. Manage it in the router dashboard.':'Active blacklist entries · verify connectivity on the device after changes.';
 for(const rule of rules){
  const device=state.devices?.find(d=>d.mac.toLowerCase()===rule.mac.toLowerCase());
  const row=document.createElement('div');row.className='blocked-card';
  const info=document.createElement('div');info.className='blocked-info';
  const title=document.createElement('h4');title.textContent=deviceName(rule.mac,device);
  const detail=document.createElement('p');detail.textContent=(device?.ip||'IP unavailable')+' · '+rule.ssid.replace('-',' ');
  const mac=document.createElement('p');mac.className='mac-line';mac.textContent=rule.mac;mac.append(copyButton(rule.mac));
  info.append(title,detail,mac);
  const actions=document.createElement('div');actions.className='blocked-actions';
  const badge=document.createElement('span');badge.className=active?'blocked-badge':'inactive-badge';badge.textContent=active?'Blocked by rule':'Inactive rule';
  const rename=document.createElement('button');rename.type='button';rename.className='quiet';rename.textContent='Name device';rename.onclick=async()=>{const name=prompt('Device name (maximum 80 characters)',state.labels[rule.mac]||'');if(name===null)return;if(name.length>80)return toast('Maximum 80 characters.');try{await post('/api/label',{mac:rule.mac,name});await refresh()}catch(e){toast(e.message)}};
  const unblock=document.createElement('button');unblock.type='button';unblock.className='quiet inline-unblock';unblock.textContent='Unblock';unblock.disabled=!active||routerBusy;unblock.onclick=()=>{if(confirm('Unblock '+deviceName(rule.mac,device)+' ('+rule.mac+') on '+rule.ssid+'?'))routerCall('/api/router/change',{action:'unblock',mac:rule.mac,ssid:rule.ssid})};
  actions.append(badge,rename,unblock);row.append(info,actions);list.append(row);
 }
 if(!rules.length){const p=document.createElement('p');p.className='rules-empty';p.textContent=active?'No blocked devices.':demo?'Exit demo to view real access rules.':'No active blocked-device list to display.';list.append(p)}
}

let monitorChanging=false;
async function setMonitor(enabled){
 await post('/api/monitor',{enabled,interface:$('interface').value?Number($('interface').value):null});
 state.monitor=enabled;renderMonitoring();
}
async function requestScanSoon(){try{if(!state.scanning)await post('/api/scan',{interface:state.interface?.index||null})}catch(e){} }
$('monitorToggle').onclick=async()=>{if(demo)return toast('Exit demo before monitoring your real network.');if(monitorChanging)return;monitorChanging=true;try{await setMonitor(!state.monitor);await refresh()}catch(e){message(e.message)}finally{monitorChanging=false}};
$('interface').onchange=async()=>{if(state.monitor&&!demo){try{await setMonitor(true)}catch(e){message(e.message)}}};
function renderMonitoring(){
 if(state.interface?.gateway&&!routerConnected&&!$('routerIP').value){$('routerIP').value=state.interface.gateway;$('routerLink').href='http://'+state.interface.gateway;}
 const enabled=!demo&&state.monitor;
 $('monitorBadge').textContent=demo?'● Demo data':enabled?'● Live monitoring on':'● Live monitoring paused';
 $('monitorBadge').className='connection-badge'+(enabled?' connected':'');
 $('monitorToggle').textContent=enabled?'Pause monitoring':'Start live monitoring';
 $('monitorTiming').textContent=enabled?(state.scanning?'Scanning now…':`Next scan ${state.next_scan?new Date(state.next_scan*1000).toLocaleTimeString():'shortly'} · 10-second pause between scans`):'Start monitoring to update the radar automatically.';
 $('activityList').replaceChildren();
 const events=demo?[]:[...(state.events||[])].reverse().slice(0,12);
 for(const event of events){const d=state.devices?.find(d=>d.mac===event.mac);const row=document.createElement('div');row.className='activity-row';const label=document.createElement('span');label.textContent=deviceName(event.mac,d)+' · '+(event.kind==='seen'?'Detected responding':'No longer responding');label.className=event.kind==='seen'?'status':'cached';const detail=document.createElement('small');detail.textContent=event.mac+' · '+new Date(event.time*1000).toLocaleTimeString();row.append(label,detail);$('activityList').append(row)}
 if(!events.length){const p=document.createElement('p');p.textContent=demo?'Activity is hidden in demo mode.':'New and missing responding devices will appear here.';$('activityList').append(p)}
 // Restore selection after a browser refresh without guessing between interfaces.
 if(state.interface&&!$('interface').value&&[...$('interface').options].some(o=>Number(o.value)===state.interface.index))$('interface').value=String(state.interface.index);
}

$('routerProfile').onchange=()=>{const supported=$('routerProfile').value==='hg8546m';$('profileHelp').textContent=supported?'HG8546M access controls are experimental. Discovery does not require router login.':'Discovery and radar remain available. Automatic blocking is unavailable for this router.';updateRouterControls()};
function updateOpsClock(){$('opsClock').textContent=new Date().toLocaleTimeString('en-GB',{hour12:false})}updateOpsClock();setInterval(updateOpsClock,1000);
