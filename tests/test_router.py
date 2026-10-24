import unittest
from router import Router, parse_page, DOMAIN, login_compatibility

def page(enabled=1,mode=0,rules=()):
 rows=','.join('new stMacFilter("%s.%s","%s","%s")'%(DOMAIN,i+1,ssid,mac) for i,(ssid,mac) in enumerate(rules))
 return "var enableFilter = '%s';var Mode = '%s';var MacFilterSrc = new Array(%s%snull);<input name='onttoken' value='test-token'>"%(enabled,mode,rows,',' if rows else '')

class RouterTests(unittest.TestCase):
 def test_parse(self):
  s=parse_page(page(rules=[('SSID-1','02:00:00:00:00:02')]))
  self.assertEqual(s['rules'][0]['mac'],'02:00:00:00:00:02');self.assertTrue(s['enabled']);self.assertEqual(s['mode'],'blacklist')
  escaped=page(rules=[('SSID-1','02:00:00:00:00:02')]).replace('SSID-1','SSID\\x2d1').replace('02:00','02\\x3a00')
  self.assertEqual(parse_page(escaped)['rules'][0]['ssid'],'SSID-1')
 def test_reject_login_page(self):
  with self.assertRaises(ValueError):parse_page('<html>Login</html>')
 def router(self,html):
  r=Router();r.opener=True;r.protected={'02:00:00:00:00:01'};r.read=lambda:parse_page(html);return r
 def test_refuse_unsafe_changes(self):
  for html,mac in [(page(enabled=0),'02:00:00:00:00:02'),(page(mode=1),'02:00:00:00:00:02'),(page(),'02:00:00:00:00:01')]:
   r=self.router(html);r.request=lambda *args:self.fail('Should not write')
   with self.assertRaises(ValueError):r.change('block',mac,'SSID-1')
 def test_verified_add_and_delete(self):
  mac='02:00:00:00:00:02';existing=('SSID-1','02:00:00:00:00:03')
  for action,before,after in [('block',[existing],[existing,('SSID-1',mac)]),('unblock',[existing,('SSID-1',mac)],[existing])]:
   r=self.router(page());states=iter([parse_page(page(rules=before)),parse_page(page(rules=after))]);r.read=lambda:next(states);sent=[];r.request=lambda path,data:sent.append((path,data))
   result=r.change(action,mac,'SSID-1');self.assertEqual(len(result['rules']),len(after));self.assertNotIn('token',result);self.assertEqual(len(sent),1);self.assertIn('x.X_HW_Token',sent[0][1])
 def test_failed_verification(self):
  r=self.router(page());r.request=lambda *args:None
  with self.assertRaisesRegex(ValueError,'verif'):r.change('block','02:00:00:00:00:02','SSID-1')

class LoginCompatibilityTests(unittest.TestCase):
 def test_common_variants(self):
  for text in ["var CfgMode ='COMMON';", 'let CfgMode = "COMMON";', "CfgMode='common';"]:
   self.assertTrue(login_compatibility(text))
 def test_standard_flow_without_mode(self):
  self.assertTrue(login_compatibility("/asp/GetRandCount.asp /login.cgi UserName PassWord base64encode(password)"))
 def test_unsupported_challenge(self):
  with self.assertRaises(ValueError):login_compatibility("var CfgMode='DT'; /asp/GetRandCount.asp /login.cgi UserName PassWord base64encode(password)")
 def test_wrapper_rejected(self):
  self.assertFalse(login_compatibility('<html><script>location="login.asp"</script></html>'))

class TokenTests(unittest.TestCase):
 def test_token_variants(self):
  from router import normalize_login_token
  token='0123456789abcdef0123456789abcdef'
  for raw in [token, '\ufeff'+token+'\r\n', '"'+token+'"', "'"+token+"'"]:
   self.assertEqual(normalize_login_token(raw),token)
 def test_reject_html(self):
  from router import normalize_login_token
  with self.assertRaisesRegex(ValueError,'HTML page'):normalize_login_token('<html>login</html>')
