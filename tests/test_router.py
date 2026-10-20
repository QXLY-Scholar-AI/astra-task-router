import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('router',BASE/'scripts/router.py');router=importlib.util.module_from_spec(spec);spec.loader.exec_module(router)

class Router(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.models=self.root/'models.json';self.models.write_text(json.dumps({'models':[{'id':x,'reasoning_efforts':['low','medium','high']} for x in ['gpt-6-luna','gpt-6.1-sol','gpt-6-astra']]}),encoding='utf-8')
    def cli(self,*args,ok=True):
        result=subprocess.run([sys.executable,'-X','utf8',str(BASE/'scripts/router.py'),*map(str,args)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode==0,ok,result.stderr+result.stdout)
        return json.loads(result.stdout) if result.returncode==0 else result.stderr
    def plan(self,task,*extra):return self.cli('plan','--task',task,'--models',self.models,*extra)
    def install(self,*extra,ok=True):return self.cli('install','--scope','project','--root',self.root,*extra,ok=ok)
    def uninstall(self,*extra,ok=True):return self.cli('uninstall','--scope','project','--root',self.root,*extra,ok=ok)
    def test_three_routes(self):
        for task,model in [('routine','gpt-6-luna'),('standard','gpt-6.1-sol'),('deep','gpt-6-astra')]:self.assertEqual(self.plan(task,'--delegation')['model'],model)
    def test_no_delegation_or_small_task(self):
        self.assertEqual(self.plan('deep')['action'],'main-thread');self.assertEqual(self.plan('deep','--delegation','--trivial')['action'],'main-thread')
    def test_no_capabilities(self):self.assertEqual(self.cli('plan','--task','routine','--delegation')['action'],'needs-capabilities')
    def test_no_models_available(self):
        self.models.write_text('{"models":[]}',encoding='utf-8');self.assertEqual(self.plan('routine','--delegation')['action'],'main-thread')
    def test_fallback_is_explicit(self):
        self.models.write_text('{"models":[{"id":"gpt-6.1-sol","reasoning_efforts":["medium"]}]}',encoding='utf-8');self.assertTrue(self.plan('deep','--delegation')['fallback'])
    def test_supported_xhigh(self):
        self.models.write_text('{"models":[{"id":"gpt-6.1-sol","reasoning_efforts":["xhigh"]}]}',encoding='utf-8');r=self.plan('standard','--delegation');self.assertEqual(r['reasoning_effort'],'xhigh');self.assertTrue(r['review_required'])
    def test_invalid_marker_orders(self):
        with self.assertRaises(ValueError):router.replace_block(router.END+router.START,'replacement')
        with self.assertRaises(ValueError):router.replace_block(router.START,'replacement')
    def test_model_and_effort_fallback_pair(self):
        self.models.write_text('{"models":[{"id":"gpt-6.1-sol","reasoning_efforts":["xhigh"]},{"id":"gpt-6-sol","reasoning_efforts":["medium"]}]}',encoding='utf-8')
        self.assertEqual(self.plan('standard','--delegation')['model'],'gpt-6-sol')
    def test_preview_no_writes(self):
        self.install();self.assertEqual(list(self.root.iterdir()),[self.models])
    def test_install_idempotent_and_roundtrip(self):
        original=b'\xef\xbb\xbf# Existing\r\nKeep this exact text.\r\n';(self.root/'AGENTS.md').write_bytes(original)
        self.install('--apply');self.assertEqual(self.install('--apply')['action'],'unchanged');self.uninstall('--apply');self.assertEqual((self.root/'AGENTS.md').read_bytes(),original)
    def test_no_prior_agents_roundtrip(self):
        self.install('--apply');self.uninstall('--apply');self.assertFalse((self.root/'AGENTS.md').exists())
    def test_changed_user_file_refuses_uninstall(self):
        self.install('--apply');agent=self.root/'AGENTS.md';agent.write_text(agent.read_text(encoding='utf-8')+'\nNew user rule',encoding='utf-8');self.uninstall('--apply',ok=False);self.assertIn('New user rule',agent.read_text(encoding='utf-8'))
    def test_global_keeps_toml(self):
        config=self.root/'config.toml';original=b'model = "user-choice"\n';config.write_bytes(original)
        self.cli('install','--scope','global','--codex-home',self.root,'--apply');self.assertEqual(config.read_bytes(),original)
    def test_legacy_state_not_overwritten(self):
        state=self.root/'.agents/astra-task-router-state.json';state.parent.mkdir();state.write_text('{"version":1}',encoding='utf-8');self.install('--apply',ok=False)

if __name__=='__main__':unittest.main()
