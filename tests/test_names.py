import subprocess
import unittest
from unittest.mock import patch
import app
class NameTests(unittest.TestCase):
 def setUp(self):app.NAME_CACHE.clear()
 def test_lookup_and_cache(self):
  with patch('app.subprocess.run',return_value=subprocess.CompletedProcess([],0,'office-laptop.local\n','')) as run:
   self.assertEqual(app.resolve_hostname('192.168.1.2'),'office-laptop.local')
   self.assertEqual(app.resolve_hostname('192.168.1.2'),'office-laptop.local');self.assertEqual(run.call_count,1)
 def test_timeout_is_unknown(self):
  with patch('app.subprocess.run',side_effect=subprocess.TimeoutExpired([],1.5)):
   self.assertEqual(app.resolve_hostname('192.168.1.3'),'')
 def test_invalid_name(self):
  with patch('app.subprocess.run',return_value=subprocess.CompletedProcess([],0,'bad\x01name','')):
   self.assertEqual(app.resolve_hostname('192.168.1.4'),'')
 def test_frozen_build_uses_powershell_not_itself(self):
  with patch.object(app.sys,'frozen',True,create=True), patch('app.subprocess.run',return_value=subprocess.CompletedProcess([],0,'workstation.local\n','')) as run:
   self.assertEqual(app.resolve_hostname('192.168.1.8'),'workstation.local')
   self.assertEqual(run.call_args.args[0][0],'powershell.exe')
   self.assertNotIn('-c',run.call_args.args[0])
