"""Veylora: local Windows network dashboard. Python standard library only."""
import argparse
import webbrowser
import concurrent.futures
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from router import Router, SessionExpired
ROUTER = Router()

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'NetPulse'
TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Lock()
STATE = {'devices': [], 'updated': None, 'scanning': False, 'error': None, 'interface': None, 'monitor': False, 'monitor_interval': 10, 'events': [], 'next_scan': None}
MAC = re.compile(r'^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$')

def powershell(script):
    if os.name != 'nt':
        raise RuntimeError('Live discovery requires Windows. Use Demo to preview on other systems.')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script], capture_output=True, text=True, timeout=25, creationflags=0x08000000)
    if result.returncode:
        raise RuntimeError('Windows network query failed. Check your active connection and PowerShell access.')
    return json.loads(result.stdout.strip() or 'null')

def records(value):
    return value if isinstance(value, list) else [value] if value else []

def labels():
    try:
        return json.loads((DATA / 'labels.json').read_text('utf-8'))
    except (OSError, ValueError):
        return {}

def save_label(mac, name):
    mac = mac.lower().replace('-', ':')
    if not MAC.fullmatch(mac) or not isinstance(name, str) or len(name) > 80:
        raise ValueError('Use a valid MAC address and a label of at most 80 characters.')
    with LOCK:
        saved = labels()
        saved[mac] = name.strip()
        DATA.mkdir(parents=True, exist_ok=True)
        tmp = DATA / 'labels.tmp'
        tmp.write_text(json.dumps(saved, indent=2), 'utf-8')
        tmp.replace(DATA / 'labels.json')

def eligible_network(address, prefix):
    ip = ipaddress.ip_address(address)
    if ip.version != 4 or not ip.is_private or ip.is_loopback or ip.is_link_local:
        raise ValueError('Select an interface with a private local IPv4 address.')
    network = ipaddress.ip_network(f'{address}/{int(prefix)}', strict=False)
    if network.num_addresses > 256:
        raise ValueError('This first version supports networks with at most 256 addresses (/24 or smaller).')
    return network

def ping(address):
    try:
        r = subprocess.run(['ping.exe', '-n', '1', '-w', '450', str(address)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2, creationflags=0x08000000)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

NAME_CACHE = {}

def resolve_hostname(address):
    cached = NAME_CACHE.get(address)
    if cached and time.time() - cached[0] < 300:
        return cached[1]
    name = ''
    try:
        if getattr(sys, 'frozen', False):
            # A packaged executable cannot run Python snippets with `-c`.
            # Addresses originate from validated local IPv4 discovery.
            ipaddress.IPv4Address(address)
            script = "$t=[System.Net.Dns]::GetHostEntryAsync('"+address+"'); if ($t.Wait(1000)) { $t.Result.HostName }"
            command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script]
        else:
            command = [sys.executable, '-c', 'import socket,sys; print(socket.gethostbyaddr(sys.argv[1])[0])', address]
        result = subprocess.run(command, capture_output=True, text=True, timeout=1.5,
            creationflags=0x08000000 if os.name == 'nt' else 0)
        candidate = result.stdout.strip() if result.returncode == 0 else ''
        if candidate and len(candidate) <= 253 and not any(ord(c) < 32 for c in candidate):
            name = candidate
    except (OSError, subprocess.TimeoutExpired):
        pass
    NAME_CACHE[address] = (time.time(), name)
    return name

def probe_network(network):
    # A separate .NET Ping instance per address; no shell interpolation of user text.
    addresses = ','.join("'" + str(ip) + "'" for ip in network.hosts())
    script = """$items = @(%s) | ForEach-Object {
        $p = New-Object System.Net.NetworkInformation.Ping
        [pscustomobject]@{ Address=$_; Ping=$p; Task=$p.SendPingAsync([string]$_,650) }
    }
    $tasks = [System.Threading.Tasks.Task[]]@($items | ForEach-Object {$_.Task})
    if ($tasks.Count -gt 0) { [void][System.Threading.Tasks.Task]::WaitAll($tasks,2500) }
    @($items | Where-Object { $_.Task.Status -eq 'RanToCompletion' -and $_.Task.Result.Status -eq 'Success' } | ForEach-Object {$_.Address}) | ConvertTo-Json -Compress
    """ % addresses
    try:
        responding = set(records(powershell(script)))
        return {str(ip):str(ip) in responding for ip in network.hosts()}
    except Exception:
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
            return dict(zip(map(str, network.hosts()), pool.map(ping, network.hosts())))


def reconcile_presence(previous, current, now):
    known={d['mac']:dict(d) for d in previous}
    observations={d['mac']:dict(d) for d in current}
    events=[];merged=[]
    for mac in known.keys() | observations.keys():
        old=known.get(mac,{})
        seen=observations.get(mac)
        d={**old,**(seen or {})}
        if seen and seen['status']=='Responding':
            d.update(misses=0,present=True,last_seen=now,status='Responding')
            if not old.get('present'):events.append({'mac':mac,'kind':'seen','time':now,'ip':d['ip']})
        else:
            misses=old.get('misses',0)+1
            d['misses']=misses
            if old.get('present') and misses<3:
                d.update(present=True,status='Checking…')
            else:
                d.update(present=False,status='Not responding' if old.get('last_seen') else 'Cached / unconfirmed')
                if old.get('present'):events.append({'mac':mac,'kind':'lost','time':now,'ip':d['ip']})
        merged.append(d)
    return sorted(merged,key=lambda d:ipaddress.ip_address(d['ip'])),events


def monitor_loop():
    while True:
        with LOCK:
            due=STATE['monitor'] and not STATE['scanning'] and (STATE['next_scan'] is None or time.time()>=STATE['next_scan'])
            index=MONITOR_INDEX
            if due:STATE.update(scanning=True,error=None)
        if due:scan(index)
        time.sleep(1)


MONITOR_INDEX=None

def configure_monitor(enabled,index):
    global MONITOR_INDEX
    with LOCK:
        MONITOR_INDEX=index
        STATE['monitor']=enabled
        if enabled:STATE['next_scan']=time.time()
        DATA.mkdir(parents=True,exist_ok=True)
        tmp=DATA/'monitor.tmp';tmp.write_text(json.dumps({'enabled':enabled,'interface':index}),'utf-8');tmp.replace(DATA/'monitor.json')


def load_monitor():
    global MONITOR_INDEX
    try:
        settings=json.loads((DATA/'monitor.json').read_text('utf-8'))
        MONITOR_INDEX=int(settings['interface']) if settings.get('interface') is not None else None
        STATE['monitor']=settings.get('enabled') is True
    except (OSError,ValueError,TypeError):pass


def scan(index):
    try:
        interfaces = records(powershell('Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | ForEach-Object { [pscustomobject]@{ index=$_.InterfaceIndex; name=$_.InterfaceAlias; ip=$_.IPv4Address[0].IPAddress; prefix=$_.IPv4Address[0].PrefixLength; gateway=$_.IPv4DefaultGateway[0].NextHop } } | ConvertTo-Json -Compress'))
        if not interfaces:
            raise ValueError('No connected IPv4 interface with a gateway was found.')
        if index is None and len(interfaces) > 1:
            raise ValueError('Multiple network interfaces found. Select one before scanning.')
        interface = next((i for i in interfaces if index is None or int(i['index']) == index), None)
        if not interface:
            raise ValueError('The selected interface is no longer available.')
        network = eligible_network(interface['ip'], interface['prefix'])
        replies = probe_network(network)
        rows = records(powershell(f'Get-NetNeighbor -AddressFamily IPv4 -InterfaceIndex {int(interface["index"])} | Select-Object IPAddress,LinkLayerAddress,State | ConvertTo-Json -Compress'))
        devices = []
        for row in rows:
            mac = str(row.get('LinkLayerAddress', '')).lower().replace('-', ':')
            try:
                address = ipaddress.ip_address(row['IPAddress'])
            except ValueError:
                continue
            if address not in network or address in (network.network_address, network.broadcast_address) or not MAC.fullmatch(mac) or mac in ('00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff'):
                continue
            devices.append({'ip': str(address), 'mac': mac, 'status': 'Responding' if replies.get(str(address)) else 'Cached / unconfirmed', 'role': 'Router' if str(address) == interface['gateway'] else 'Device', 'neighbor_state': row['State']})
        # Reverse DNS is best-effort; missing names remain explicitly unknown.
        responsive = [d for d in devices if d['status'] == 'Responding'][:64]
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            resolved = list(pool.map(resolve_hostname, [d['ip'] for d in responsive]))
        for device, hostname in zip(responsive, resolved):
            device['hostname'] = hostname
        devices.sort(key=lambda d: ipaddress.ip_address(d['ip']))
        with LOCK:
            old = STATE['devices'] if STATE['interface'] and STATE['interface']['index']==interface['index'] else []
            devices, events = reconcile_presence(old, devices, time.time())
            STATE.update(devices=devices, interface=interface, updated=time.time(), error=None, events=(STATE['events']+events)[-60:])
    except Exception as exc:
        with LOCK:
            STATE['error'] = str(exc)
    finally:
        with LOCK:
            STATE['scanning'] = False
            STATE['next_scan'] = time.time() + STATE['monitor_interval'] if STATE['monitor'] else None

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def valid_host(self):
        return self.headers.get('Host') in ('127.0.0.1:8765', 'localhost:8765')

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Invalid host'})
        if self.path == '/api/state':
            with LOCK:
                snapshot = dict(STATE)
            return self.reply(200, {**snapshot, 'labels': labels(), 'token': TOKEN})
        if self.path == '/api/interfaces':
            try:
                value = powershell('Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } | ForEach-Object { [pscustomobject]@{ index=$_.InterfaceIndex; name=$_.InterfaceAlias; ip=$_.IPv4Address[0].IPAddress } } | ConvertTo-Json -Compress')
                return self.reply(200, {'interfaces': records(value)})
            except Exception as exc:
                return self.reply(200, {'interfaces': [], 'error': str(exc)})
        files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
        if self.path not in files:
            return self.reply(404, {'error': 'Not found'})
        filename, mime = files[self.path]
        data = (ROOT / 'static' / filename).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime + '; charset=utf-8')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-NetPulse-Token') != TOKEN or self.headers.get('Origin') not in ('http://127.0.0.1:8765', 'http://localhost:8765'):
            return self.reply(403, {'error': 'Reload Veylora and try again.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('Invalid request size')
            body = json.loads(self.rfile.read(length))
            if self.path.startswith('/api/router/'):
                try:
                    if self.path == '/api/router/connect':
                        result = ROUTER.connect(body['address'], body['username'], body['password'], body['protected'])
                    elif self.path == '/api/router/status':
                        result = ROUTER.status()
                    elif self.path == '/api/router/change':
                        result = ROUTER.change(body['action'], body['mac'], body['ssid'])
                    elif self.path == '/api/router/disconnect':
                        ROUTER.disconnect()
                        result = {'disconnected': True}
                    else:
                        return self.reply(404, {'error': 'Not found'})
                    return self.reply(200, result)
                except Exception as exc:
                    message = str(exc) if isinstance(exc, ValueError) else 'Router request failed or timed out. Check router access, then reconnect. No automatic retry was made.'
                    return self.reply(401 if isinstance(exc,SessionExpired) else 400, {'error': message, **ROUTER.error_context()})
            if self.path == '/api/monitor':
                enabled=body.get('enabled')
                if not isinstance(enabled,bool):raise ValueError('Invalid monitor setting')
                index=body.get('interface')
                if index is not None:index=int(index)
                configure_monitor(enabled,index)
                return self.reply(200, {'ok': True})
            if self.path == '/api/label':
                save_label(body['mac'], body['name'])
                return self.reply(200, {'ok': True})
            if self.path == '/api/scan':
                index = body.get('interface')
                if index is not None:
                    index = int(index)
                with LOCK:
                    if STATE['scanning']:
                        return self.reply(409, {'error': 'A scan is already running.'})
                    STATE.update(scanning=True, error=None)
                threading.Thread(target=scan, args=(index,), daemon=True).start()
                return self.reply(202, {'ok': True})
            return self.reply(404, {'error': 'Not found'})
        except (ValueError, KeyError, TypeError):
            return self.reply(400, {'error': 'Invalid request. Check the submitted values.'})

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description='Veylora — independent local network observatory. Created by Denis Kiriaku.')
    parser.add_argument('--no-browser',action='store_true',help='Start without opening a browser tab')
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    load_monitor()
    threading.Thread(target=monitor_loop,daemon=True).start()
    print('Veylora v0.6 is running at http://127.0.0.1:8765 — Ctrl+C to stop.')
    if not args.no_browser:
        opener=threading.Timer(0.8,lambda:webbrowser.open('http://127.0.0.1:8765'))
        opener.daemon=True
        opener.start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
