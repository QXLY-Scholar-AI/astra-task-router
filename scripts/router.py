"""Local routing plans and reversible AGENTS installation. No model/API calls."""
import argparse
import difflib
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
START = '<!-- ASTRA-TASK-ROUTER:START -->'
END = '<!-- ASTRA-TASK-ROUTER:END -->'

def digest(data):return hashlib.sha256(data).hexdigest()
def stamp():return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_bytes(data);tmp.replace(path)
def emit(value):print(json.dumps(value,ensure_ascii=False,indent=2))

def replace_block(text,block):
    if text.count(START)!=text.count(END) or text.count(START)>1:
        raise ValueError('Managed markers malformed or duplicated; inspect before editing')
    if START in text:
        start,end=text.index(START),text.index(END)+len(END)
        if text.index(END)<start:raise ValueError('Managed markers reversed')
        return text[:start]+block.strip()+text[end:]
    return text+('\n\n' if text and not text.endswith('\n\n') else '')+block.strip()+'\n'

def locations(args):
    root=args.root.resolve() if args.scope=='project' else args.codex_home.resolve()
    return root/'AGENTS.md',root/('.agents/astra-task-router-state.json' if args.scope=='project' else 'astra-task-router-state.json')

def plan(args):
    policy=json.loads((BASE/'references/routing-policy.json').read_text(encoding='utf-8'))
    route=policy['routes'][args.task]
    result={'task_type':args.task,'root':'preserve-current','executes_model':False,'policy_version':policy['version'],'worker_limit':1}
    if args.trivial or not args.delegation:return {**result,'action':'main-thread','reason':'task too small or delegation not authorized'}
    if not args.models:return {**result,'action':'needs-capabilities','reason':'Read the host model list before selecting a worker'}
    host=json.loads(args.models.read_text(encoding='utf-8-sig'));models=host.get('models',[])
    if not isinstance(models,list) or any(not isinstance(m,dict) or not isinstance(m.get('id'),str) or not isinstance(m.get('reasoning_efforts'),list) for m in models):
        raise ValueError('models must contain id and reasoning_efforts arrays')
    available={m['id']:m for m in models}
    candidates=[m for m in route['models'] if m in available]
    if not candidates:return {**result,'action':'main-thread','reason':'No supported model from this route is exposed by the host'}
    selected=effort=None
    # Prefer the intended effort (or normal nearby levels) across candidates
    # before using an unusually high level just because it exists on model #1.
    for effort_order in [[route['reasoning'],'medium','low','high','minimal','none'],['xhigh','max','ultra']]:
        for candidate in candidates:
            level=next((e for e in effort_order if e in available[candidate]['reasoning_efforts']),None)
            if level is not None:selected,effort=candidate,level;break
        if selected:break
    if effort is None:return {**result,'action':'needs-capabilities','reason':'Available route models expose no supported reasoning effort'}
    return {**result,'action':'delegate','model':selected,'reasoning_effort':effort,'fallback':selected!=route['models'][0],
            'review_required':args.task=='deep' or selected!=route['models'][0] or effort!=route['reasoning'],'identity_verified':False,
            'identity_note':'Explicit selection plan, not proof of an executed model identity'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    route=sub.add_parser('plan');route.add_argument('--task',choices=['routine','standard','deep'],required=True)
    route.add_argument('--models',type=Path);route.add_argument('--delegation',action='store_true');route.add_argument('--trivial',action='store_true')
    for command in ['install','status','uninstall']:
        item=sub.add_parser(command);item.add_argument('--scope',choices=['project','global'],required=True)
        item.add_argument('--root',type=Path);item.add_argument('--codex-home',type=Path,default=Path.home()/'.codex')
        if command!='status':item.add_argument('--apply',action='store_true',help='Without this flag show a preview only')
    args=parser.parse_args()
    if args.command=='plan':emit(plan(args));return
    if args.scope=='project' and not args.root:parser.error('--root required; use the explicitly selected project root')
    agent,state_path=locations(args);raw=agent.read_bytes() if agent.exists() else b'';text=raw.decode('utf-8-sig')
    state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else None
    if args.command=='status':
        emit({'scope':args.scope,'agents':str(agent),'state':state,'block_present':START in text,'config_toml_changed':False,'configured':bool(state and START in text),'model_execution_verified':False});return
    if args.command=='install':
        if state and state.get('version')!=2:raise ValueError('Legacy state found: inspect its backups and owned fields before migration')
        if state and digest(raw)!=state['installed_sha256']:raise ValueError('AGENTS changed after installation; reconcile the diff before reinstalling')
        block=(BASE/'references/managed-block.md').read_text(encoding='utf-8');updated=replace_block(text,block).encode('utf-8')
        if raw.startswith(b'\xef\xbb\xbf'):updated=b'\xef\xbb\xbf'+updated
        if state and digest(updated)==state['installed_sha256']:emit({'action':'unchanged','agents':str(agent)});return
    else:
        if not state or state.get('version')!=2:raise ValueError('No v2 installation record. Legacy installations require their own backups and diff')
        if digest(raw)!=state['installed_sha256']:raise ValueError('AGENTS changed after installation; refuse to overwrite unrelated edits')
        updated=Path(state['backup']).read_bytes()
        if digest(updated)!=state['previous_sha256']:raise ValueError('Installation backup integrity failure')
    diff=''.join(difflib.unified_diff(text.splitlines(True),updated.decode('utf-8-sig').splitlines(True),fromfile=str(agent),tofile=str(agent)))
    if not args.apply:emit({'action':'preview','command':args.command,'scope':args.scope,'agents':str(agent),'state_path':str(state_path),'diff':diff,'config_toml_changed':False});return
    if args.command=='install':
        backup=state_path.parent/'astra-task-router-backups'/(stamp()+'.AGENTS.md');write(backup,raw)
        # Preserve the original rollback point across policy upgrades.
        state={'version':2,'scope':args.scope,'agents':str(agent),'created':stamp(),'backup':state['backup'] if state else str(backup),
               'previous_existed':state['previous_existed'] if state else agent.exists(),
               'previous_sha256':state['previous_sha256'] if state else digest(raw),'installed_sha256':digest(updated),
               'config_toml_changed':False,'root_model':'preserve-current'}
        write(state_path,json.dumps(state,ensure_ascii=False,indent=2).encode('utf-8'));write(agent,updated)
    else:
        if state['previous_existed']:write(agent,updated)
        else:agent.unlink()
        state_path.replace(state_path.with_name('astra-task-router-uninstalled-'+stamp()+'.json'))
    emit({'action':args.command,'agents':str(agent),'scope':args.scope,'config_toml_changed':False,'backups_preserved':True})

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError) as error:raise SystemExit(str(error))
