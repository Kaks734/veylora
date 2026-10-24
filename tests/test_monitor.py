import unittest
from unittest.mock import patch
import app
from router import Router,SessionExpired
from test_router import page

class PresenceTests(unittest.TestCase):
 def device(self,status='Responding'):
  return {'mac':'02:00:00:00:00:02','ip':'192.168.1.2','status':status,'role':'Device'}
 def test_seen_lost_and_return(self):
  devices,events=app.reconcile_presence([],[self.device()],100)
  self.assertTrue(devices[0]['present']);self.assertEqual(events[0]['kind'],'seen')
  for now in (110,120):
   devices,events=app.reconcile_presence(devices,[],now)
   self.assertTrue(devices[0]['present']);self.assertEqual(events,[])
  devices,events=app.reconcile_presence(devices,[],130)
  self.assertFalse(devices[0]['present']);self.assertEqual(events[0]['kind'],'lost')
  devices,events=app.reconcile_presence(devices,[self.device()],140)
  self.assertTrue(devices[0]['present']);self.assertEqual(devices[0]['misses'],0);self.assertEqual(events[0]['kind'],'seen')
 def test_cached_is_never_confirmed(self):
  devices,events=app.reconcile_presence([],[self.device('Cached / unconfirmed')],100)
  self.assertFalse(devices[0]['present']);self.assertEqual(events,[])
 def test_stable_response_no_duplicate_event(self):
  old,_=app.reconcile_presence([],[self.device()],100)
  new,events=app.reconcile_presence(old,[self.device()],110)
  self.assertEqual(events,[]);self.assertEqual(new[0]['last_seen'],110)
 def test_parallel_probe(self):
  with patch('app.powershell',return_value=['192.168.1.1']):
   replies=app.probe_network(app.eligible_network('192.168.1.1',30))
   self.assertEqual(replies,{'192.168.1.1':True,'192.168.1.2':False})

class SessionTests(unittest.TestCase):
 def test_real_expiry_invalidates_session(self):
  r=Router();r.opener=object();r.request=lambda *args:'<input id="txt_Password">'
  with self.assertRaises(SessionExpired):r.read()
  self.assertIsNone(r.opener)
 def test_validation_keeps_session(self):
  r=Router();session=object();r.opener=session;r.read=lambda:None;r.protected={'02:00:00:00:00:01'}
  with self.assertRaises(ValueError):r.change('block','02:00:00:00:00:01','SSID-1')
  self.assertIs(r.opener,session);self.assertTrue(r.error_context()['session_active'])
 def test_write_timeout_readback_success_no_resubmit(self):
  from router import parse_page
  r=Router();r.opener=object();r.protected=set();mac='02:00:00:00:00:02'
  reads=iter([parse_page(page()),parse_page(page(rules=[('SSID-1',mac)]))]);r.read=lambda:next(reads)
  calls=[]
  def write(path,data):calls.append(path);raise TimeoutError()
  r.request=write
  self.assertEqual(r.change('block',mac,'SSID-1')['rules'][0]['mac'],mac)
  self.assertEqual(len(calls),1);self.assertIsNotNone(r.opener)
 def test_no_session_restore_response(self):
  self.assertEqual(Router().status(),{'disconnected':True})
