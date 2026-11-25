import os
from pathlib import Path
import tempfile
import unittest
from local_config import load_env, parse_env, ConfigError
from scripts.configure_local import save_config

class LocalConfigTests(unittest.TestCase):
    def test_missing_file_does_not_change_environment(self):
        with tempfile.TemporaryDirectory() as d:
            env={};self.assertFalse(load_env(Path(d)/'.env',env));self.assertEqual(env,{})
    def test_quotes_comments_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.env';p.write_text('# comment\nOPENAI_API_KEY="fake-key"\nOPENAI_MODEL=test-model\n')
            env={'OPENAI_MODEL':'shell-model'};load_env(p,env)
            self.assertEqual(env,{'OPENAI_API_KEY':'fake-key','OPENAI_MODEL':'shell-model'})
    def test_no_shell_expansion(self):
        self.assertEqual(parse_env('OPENAI_API_KEY=$(do-not-run)')['OPENAI_API_KEY'],'$(do-not-run)')
    def test_invalid_file_is_atomic_and_error_does_not_leak(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.env';p.write_text('OPENAI_MODEL=test\nSECRET_FAKE=private-marker')
            env={}
            with self.assertRaises(ConfigError) as cm:load_env(p,env)
            self.assertEqual(env,{})
            self.assertNotIn('private-marker',str(cm.exception))
    def test_save_permissions_update_and_port(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.env';p.write_text('PORT=9000\n')
            save_config('fake-key','test-model',p)
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            self.assertEqual(parse_env(p.read_text())['PORT'],'9000')
            save_config('fake-new','test-model',p)
            self.assertEqual(parse_env(p.read_text())['OPENAI_API_KEY'],'fake-new')
            self.assertEqual(list(Path(d).iterdir()),[p])
    def test_invalid_input_preserves_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.env';p.write_text('PORT=9000\n')
            with self.assertRaises(ConfigError):save_config('bad\nkey','model',p)
            self.assertEqual(p.read_text(),'PORT=9000\n')
    def test_symlink_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'.env';target=Path(d)/'other';target.write_text('unchanged');p.symlink_to(target)
            with self.assertRaises(ConfigError):save_config('fake-key','model',p)
            self.assertEqual(target.read_text(),'unchanged')
