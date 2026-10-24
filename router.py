"""Experimental HG8546M COMMON firmware adapter; credentials kept in memory only."""
import base64
from http.cookiejar import Cookie, CookieJar
from html.parser import HTMLParser
import ipaddress
import json
import re
import threading
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler, ProxyHandler

PAGE = '/html/bbsp/wlanmacfilter/wlanmacfilter.asp'
DOMAIN = 'InternetGatewayDevice.X_HW_Security.WLANMacFilter'
MAC = re.compile(r'^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$')

class SessionExpired(ValueError):
 pass

class TokenParser(HTMLParser):
 def __init__(self): super().__init__(); self.token=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='input' and a.get('name')=='onttoken': self.token=a.get('value')

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if urlsplit(req.full_url).netloc != urlsplit(newurl).netloc: raise ValueError('Router redirected to a different host.')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def parse_page(text):
 def setting(name):
  m=re.search(r'var\s+'+name+r"\s*=\s*'([01])'",text)
  if not m: raise ValueError('Unsupported router response or expired session. Reconnect.')
  return int(m.group(1))
 token=TokenParser();token.feed(text)
 if not token.token: raise ValueError('Router security token missing. Reconnect.')
 rules=[]
 for domain,ssid,mac in re.findall(r'new\s+stMacFilter\("([^"\n]*)","([^"\n]*)","([^"\n]*)"\)',text):
  def decode(v): return re.sub(r'\\x([0-9a-fA-F]{2})',lambda m:chr(int(m.group(1),16)),v)
  domain,ssid,mac=map(decode,(domain,ssid,mac));mac=mac.lower()
  if not re.fullmatch(re.escape(DOMAIN)+r'\.\d+',domain) or not re.fullmatch(r'SSID-[1-8]',ssid) or not MAC.fullmatch(mac): raise ValueError('Unrecognized rule format; no changes made.')
  rules.append({'domain':domain,'ssid':ssid,'mac':mac})
 # Refuse partial parsing rather than treating unparsed rules as absent.
 source=re.search(r'var\s+MacFilterSrc\s*=\s*(.*?);',text,re.S)
 if not source or source.group(1).count('new stMacFilter')!=len(rules): raise ValueError('Could not read all rules; no changes made.')
 return {'enabled':bool(setting('enableFilter')),'mode':'blacklist' if setting('Mode')==0 else 'allowlist','rules':rules,'token':token.token}

def login_compatibility(text):
 """Recognize the observed protocol independently of JS spacing/quote style."""
 match=re.search(r"\bCfgMode\s*=\s*([\"'])([^\"']{1,64})\1",text,re.I)
 mode=match.group(2).strip().upper() if match else None
 if mode in ('DT','TRIPLET','TRIPLETVOICE'):
  raise ValueError('This router uses a different login protocol (challenge or verification code). No login attempt was sent.')
 standard=all(re.search(pattern,text,re.I) for pattern in [
  r'GetRandCount\.asp', r'login\.cgi', r'UserName', r'PassWord', r'base64encode\s*\('])
 if mode=='COMMON' or standard:
  return True
 return False

def normalize_login_token(raw):
 text=raw.lstrip('\ufeff').strip()
 if text.startswith('"'):
  try:
   decoded=json.loads(text)
   if isinstance(decoded,str): text=decoded.strip()
  except ValueError: pass
 elif len(text)>=2 and text[0]==text[-1]=="'":
  text=text[1:-1].strip()
 if not re.fullmatch(r'[a-zA-Z0-9_-]{1,256}',text):
  kind='HTML page' if '<html' in text.lower() or '<!doctype' in text.lower() else 'empty response' if not text else 'unrecognized response'
  raise ValueError('Login-token endpoint returned '+kind+' ('+str(len(raw))+' characters). No credentials were submitted. Confirm you restarted the latest NetPulse build and check the router address.')
 return text

class Router:
 def __init__(self): self.lock=threading.Lock();self.opener=None;self.base=None;self.protected=set();self.last_login=0;self.last_state=None;self.checked=None
 def request(self,path,data=None):
  req=Request(self.base+path,data=urlencode(data).encode() if data is not None else None,headers={'Referer':self.base+PAGE,'Origin':self.base})
  with self.opener.open(req,timeout=12) as r:
   if urlsplit(r.url).netloc!=urlsplit(self.base).netloc: raise ValueError('Unexpected redirect.')
   return r.read(2_000_000).decode('utf-8',errors='replace')
 def read(self):
  text=self.request(PAGE)
  if re.search(r'(?:id|name)\s*=\s*[\"\']txt_Password',text,re.I):
   self.opener=None
   raise SessionExpired('Router session expired. Sign in once to continue; no credentials were stored.')
  state=parse_page(text);self.last_state=state;self.checked=time.time()
  return state
 def public(self,state):
  return {**{k:v for k,v in state.items() if k!='token'},'checked':self.checked,'router_ip':urlsplit(self.base).hostname if self.base else None,'protected_mac':next(iter(self.protected),'')}
 def error_context(self):
  return {'session_active':self.opener is not None,'last_state':self.public(self.last_state) if self.last_state and self.opener else None}
 def connect(self,address,username,password,protected):
  with self.lock:
   if time.monotonic()-self.last_login<10: raise ValueError('Wait 10 seconds before another login attempt.')
   self.last_login=time.monotonic();self.opener=None
   ip=ipaddress.ip_address(address)
   if ip.version!=4 or not ip.is_private or ip.is_loopback or ip.is_link_local: raise ValueError('Enter a private router IPv4 address.')
   protected=protected.lower().replace('-',':').strip()
   if not MAC.fullmatch(protected) or int(protected[:2],16)&1 or protected=='00:00:00:00:00:00': raise ValueError('Enter your Windows Wi-Fi adapter MAC address to protect it from blocking.')
   if not isinstance(username,str) or not 1<=len(username)<=31 or not isinstance(password,str) or not 1<=len(password)<=127 or not password.isascii(): raise ValueError('Enter a username and ASCII password within router limits.')
   self.base='http://'+str(ip);jar=CookieJar();self.opener=build_opener(ProxyHandler({}),HTTPCookieProcessor(jar),NoRedirect())
   try:
    login=self.request('/login.asp')
    if not login_compatibility(login):
     # Some firmware serves a wrapper or redirect script at /login.asp.
     login=self.request('/')
     if not login_compatibility(login):
      raise ValueError('Router returned an unrecognized login page at /login.asp and /. No credentials were submitted. Open the router dashboard, log out, and retry. If this persists, send the logged-out main document response without credentials.')
    cnt=normalize_login_token(self.request('/asp/GetRandCount.asp',{}))
    jar.set_cookie(Cookie(0,'Cookie','body:Language:english:id=-1',None,False,str(ip),False,False,'/',True,False,None,True,None,None,{}))
    self.request('/login.cgi',{'UserName':username,'PassWord':base64.b64encode(password.encode('ascii')).decode(),'x.X_HW_Token':cnt})
    state=self.read();self.protected={protected};return self.public(state)
   except Exception:
    self.opener=None;raise
 def status(self):
  with self.lock:
   if not self.opener: return {'disconnected':True}
   return self.public(self.read())
 def change(self,action,mac,ssid):
  with self.lock:
   if not self.opener: raise ValueError('Connect to your router first.')
   mac=mac.lower().replace('-',':').strip()
   if not MAC.fullmatch(mac) or int(mac[:2],16)&1 or mac=='00:00:00:00:00:00' or not re.fullmatch(r'SSID-[1-8]',ssid): raise ValueError('Invalid device MAC or SSID.')
   if mac in self.protected: raise ValueError('Your protected adapter cannot be blocked or changed.')
   if action not in ('block','unblock'): raise ValueError('Unsupported action.')
   current=self.read()
   if current['mode']!='blacklist': raise ValueError('Router is in allowlist mode. Manage it manually; no changes made.')
   if not current['enabled']: raise ValueError('WLAN filtering is disabled. Review all existing rules in the router before enabling it there, then refresh NetPulse.')
   found=[r for r in current['rules'] if r['mac']==mac and r['ssid']==ssid]
   if action=='block' and found or action=='unblock' and not found:return self.public(current)
   if action=='block':
    if sum(r['ssid']==ssid for r in current['rules'])>=8:raise ValueError('This SSID already has 8 rules.')
    path='/add.cgi?'+urlencode({'x':DOMAIN,'RequestFile':PAGE[1:]})
    data={'x.SourceMACAddress':mac,'x.SSIDName':ssid,'x.Enable':'1','x.X_HW_Token':current['token']}
   else:
    path='/del.cgi?'+urlencode({'x':DOMAIN,'RequestFile':PAGE[1:]});data={r['domain']:'' for r in found};data['x.X_HW_Token']=current['token']
   # Submit a mutation once. Only read-back checks may be retried.
   try:self.request(path,data)
   except Exception:pass
   after=None
   for attempt in range(3):
    if attempt:time.sleep(0.25)
    try:
     after=self.read()
     exists=any(r['ssid']==ssid and r['mac']==mac for r in after['rules'])
     if exists==(action=='block'):break
    except SessionExpired:raise
    except Exception:
     if attempt==2:raise ValueError('Saved rules could not be checked. Your session was retained; click Refresh rules. Do not repeat the action until checked.')
   if after is None:raise ValueError('Read-back unavailable. Refresh rules before retrying.')
   before_other={(r['ssid'],r['mac']) for r in current['rules'] if not(r['ssid']==ssid and r['mac']==mac)}
   after_other={(r['ssid'],r['mac']) for r in after['rules'] if not(r['ssid']==ssid and r['mac']==mac)}
   exists=any(r['ssid']==ssid and r['mac']==mac for r in after['rules'])
   if before_other!=after_other or exists!=(action=='block') or not after['enabled'] or after['mode']!='blacklist':raise ValueError('The expected rule change was not verified. Your session is retained. Click Refresh rules and inspect the router before repeating the action.')
   return self.public(after)
 def disconnect(self):
  with self.lock:self.opener=None;self.protected=set();self.last_state=None;self.checked=None
