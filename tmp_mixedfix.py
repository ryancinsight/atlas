import os, subprocess
idx=r"D:\\atlas\\.git\\atlas-rescue-hook-clean.index"; os.environ['GIT_INDEX_FILE']=idx
def read(p): return subprocess.check_output(['git','show','refs/heads/fix/hooks-rescue-push:'+p]).decode()
def put(p,s,mode='100644'):
 b=subprocess.check_output(['git','hash-object','-w','--stdin'],input=s.encode()).decode().strip(); subprocess.run(['git','update-index','--add','--cacheinfo',f'{mode},{b},{p}'],check=True)
path='.githooks/pre-push'; s=read(path); nl=chr(10)
s=s.replace('initial_rescue_tip=""'+nl+'initial_rescue_count=0'+nl,'initial_rescue_tip=""'+nl+'initial_rescue_count=0'+nl+'all_rescue=1'+nl,1)
s=s.replace('        else'+nl+'            rescue_line=""'+nl+'            break'+nl,'        else'+nl+'            all_rescue=0'+nl+'            rescue_line=""'+nl,1)
s=s.replace('    && [ "$initial_rescue_count" -eq 1 ]; then','    && [ "$initial_rescue_count" -eq 1 ] \\'+nl+'    && [ "$all_rescue" -eq 1 ]; then',1); put(path,s,'100755')
path='scripts/tests/test_atlas_rescue_push_hook.py'; s=read(path); marker='    def test_root_rescue_enumeration_failure_blocks(self):'+nl; test='    def test_malformed_remote_in_later_ref_blocks_before_any_gate(self):'+nl+'        temporary, root = self.fixture()'+nl+'        with temporary:'+nl+'            tip = git(root, "rev-parse", "HEAD")'+nl+'            malformed = "1" * 40'+nl+'            stream = (f"refs/heads/main {tip} refs/heads/main {git(root, \'rev-parse\', \'HEAD\')}\\n"'+nl+'                      f"refs/heads/other {tip} refs/heads/other {malformed}\\n")'+nl+'            result = self.run_hook(root, stream)'+nl+'            self.assertNotEqual(result.returncode, 0)'+nl+'            self.assertIn("remote commit is unavailable", result.stderr)'+nl+'            self.assertFalse((root / "auditor.log").exists())'+nl+nl
if marker not in s: raise SystemExit('marker'); s=s.replace(marker,test+marker,1); put(path,s)
tree=subprocess.check_output(['git','write-tree']).decode().strip(); parent=subprocess.check_output(['git','rev-parse','refs/heads/fix/hooks-rescue-push'],text=True).strip(); msg='fix(hooks): validate every pushed ref'+nl+nl+'Item: ATLAS-RESCUE-PUSH-HOOK-2026-09-28'+nl; c=subprocess.check_output(['git','commit-tree',tree,'-p',parent],input=msg.encode()).decode().strip(); subprocess.run(['git','update-ref','refs/heads/fix/hooks-rescue-push',c,parent],check=True); print(c)
