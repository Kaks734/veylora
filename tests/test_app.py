import http.client
import tempfile
import threading
import unittest
from pathlib import Path
import app
class Tests(unittest.TestCase):
 def test_subnet(self):
  self.assertEqual(str(app.eligible_network('192.168.1.5',24)),'192.168.1.0/24')
  for ip,p in [('8.8.8.8',24),('127.0.0.1',24),('192.168.1.1',16)]:
   with self.assertRaises(ValueError):app.eligible_network(ip,p)
 def test_labels(self):
  old=app.DATA
  try:
   with tempfile.TemporaryDirectory() as d:
    app.DATA=Path(d);app.save_label('02:00:00:00:00:01','Laptop');self.assertEqual(app.labels()['02:00:00:00:00:01'],'Laptop')
    with self.assertRaises(ValueError):app.save_label('invalid','X')
  finally:app.DATA=old
 def test_http(self):
  s=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);threading.Thread(target=s.serve_forever,daemon=True).start()
  try:
   c=http.client.HTTPConnection('127.0.0.1',s.server_port)
   for method,path,headers,expected in [('GET','/api/state',{'Host':'evil.example'},403),('POST','/api/scan',{'Host':'127.0.0.1:8765','Origin':'https://evil.example','X-NetPulse-Token':app.TOKEN},403),('GET','/',{'Host':'127.0.0.1:8765'},200)]:
    c.request(method,path,body='{}' if method=='POST' else None,headers=headers);r=c.getresponse();self.assertEqual(r.status,expected);r.read()
   c.close()
  finally:s.shutdown();s.server_close()
