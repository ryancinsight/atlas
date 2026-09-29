import os,subprocess
idx=r"D:\\atlas\\.git\\atlas-rescue-hook-clean.index"; os.environ['GIT_INDEX_FILE']=idx; nl=chr(10)
def read(p): return subprocess.check_output(['git','show','refs/heads/fix/hooks-rescue-push:'+p]).decode()
def put(p,s,mode='100644'):
 b=subprocess.check_output(['git','hash-object','-w','--stdin'],input=s.encode()).decode().strip(); subprocess.run(['git','update-index','--add','--cacheinfo',f'{mode},{b},{p}'],check=True)
p='scripts/git-hooks/pre-push'; s=read(p); old='    [ -n "$push_line" ] && push_lines+=("$push_line")'; new='    read -r push_local_ref push_sha push_remote_ref push_remote_sha'+nl+'    if [ "$push_sha" != "$zero" ] && ! outside_checkout git -C "$repo_root" cat-file -e "$push_sha^{commit}" 2>/dev/null; then echo "pre-push: BLOCKED -- pushed local commit is unavailable" >&2; exit 1; fi'+nl+'    if [ "$push_remote_sha" != "$zero" ] && ! outside_checkout git -C "$repo_root" cat-file -e "$push_remote_sha^{commit}" 2>/dev/null; then echo "pre-push: BLOCKED -- remote commit is unavailable" >&2; exit 1; fi'+nl+'    [ -n "$push_line" ] && push_lines+=("$push_line")';
if old not in s: raise SystemExit('member marker')
put(p,s,'100755')
p='scripts/atlas-secret-scan.py'; s=read(p); old='        path = raw_path.decode("utf-8", "replace")'+nl+'        blob = _git(root, "show", f"{rev}:{path}")'+nl; new='        path = raw_path.decode("utf-8", "replace")'+nl+'        tree_entry = _git(root, "ls-tree", rev, "--", path)'+nl+'        if tree_entry.returncode: raise RuntimeError(f"git ls-tree {rev}:{path} failed")'+nl+'        if tree_entry.stdout.startswith(b"160000 "): continue'+nl+'        blob = _git(root, "show", f"{rev}:{path}")'+nl;
if old not in s: raise SystemExit('scanner marker')
put(p,s.replace(old,new,1))
tree=subprocess.check_output(['git','write-tree']).decode().strip(); parent=subprocess.check_output(['git','rev-parse','refs/heads/fix/hooks-rescue-push'],text=True).strip(); msg='fix(hooks): cover gitlinks and member refs'+nl+nl+'Item: ATLAS-RESCUE-PUSH-HOOK-2026-09-28'+nl; c=subprocess.check_output(['git','commit-tree',tree,'-p',parent],input=msg.encode()).decode().strip(); subprocess.run(['git','update-ref','refs/heads/fix/hooks-rescue-push',c,parent],check=True); print(c)
