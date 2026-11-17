"""Create an isolated public source snapshot; never upload or read database data."""
from pathlib import Path
import argparse
import os
import json
import re
import hashlib
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ['frontend','shared','agent','backend','ruoyi/backend','ruoyi/frontend','ruoyi/scripts','scripts','docs','deploy','ai/scripts','assets-source/hangzhou/output','.github']
FILES = ['.gitignore','package.json','package-lock.json','ai/env-spec.json','ai/requirements-lock.txt','ai/README.md','ai/.gitignore','ruoyi/.gitignore','ruoyi/README.md','ruoyi/config/application-sky-twin.yml','ruoyi/config/maven-settings.xml']
SKIP_DIR = {'.git','.runtime','.venv','venv','node_modules','__pycache__','.cache','.idea','.vscode','target','dist','logs','data','datasets','runs','.ultralytics'}
SKIP_EXT = {'.log','.pyc','.pyo','.db','.sqlite','.sqlite3','.ibd','.rdb','.aof','.exe','.dll','.zip','.7z','.rar','.mp4','.mov','.docx','.pdf','.psd','.pt','.pth'}
SKIP_NAME = {'LEARNING_PROGRESS.md','local-secrets.json','runtime.local.json','mysql-root.cnf','mysql.ini','redis.conf','.DS_Store'}


def candidates():
    found = set()
    for folder in FOLDERS:
        base=ROOT/folder
        if not base.exists(): continue
        for current,dirs,files in os.walk(base,followlinks=False):
            dirs[:]=sorted(d for d in dirs if d not in SKIP_DIR and not (Path(current)/d).is_symlink())
            for name in sorted(files):
                path=Path(current)/name
                rel=path.relative_to(ROOT).as_posix()
                if path.is_symlink() or name in SKIP_NAME or path.suffix.lower() in SKIP_EXT: continue
                if name.startswith('~$') or name in {'.env','.env.local'} or (name.startswith('.env.') and name not in {'.env.example','.env.development','.env.production','.env.staging'}): continue
                if '.local.' in name or rel.startswith(('deploy/sites-','docs/录屏','docs/传智杯AI_WEB_旧T')): continue
                if 'credentials' in name.lower() or name.endswith(('.pem','.key','.p12','.pfx')): continue
                found.add(path)
    found.update(ROOT/p for p in FILES if (ROOT/p).is_file())
    return sorted(found,key=lambda p:p.relative_to(ROOT).as_posix())


def local_secret_values():
    values=set()
    def walk(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if isinstance(v,str) and re.search(r'password|secret|token|api.?key',k,re.I) and len(v)>=12:
                    values.add(v)
                elif isinstance(v,(dict,list)): walk(v)
        elif isinstance(obj,list):
            for v in obj: walk(v)
    for rel in ['ruoyi/config/local-secrets.json','.runtime/public-demo-credentials.json','.runtime/domestic-demo.json']:
        path=ROOT/rel
        if path.exists(): walk(json.loads(path.read_text(encoding='utf-8-sig')))
    for rel in ['agent/.env','.runtime/cpolar-skytwin.yml']:
        path=ROOT/rel
        if path.exists():
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                m=re.match(r'\s*([\w.-]*(?:KEY|TOKEN|PASSWORD|SECRET|authtoken)[\w.-]*)\s*[:=]\s*(.+)',line,re.I)
                if m:
                    v=m[2].strip().strip('"\'')
                    if len(v)>=12 and not v.startswith('${'): values.add(v)
    return values


def audit(paths):
    secrets=local_secret_values()
    issues=[]
    sizes=[]
    for path in paths:
        rel=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        raw=path.read_bytes()
        sizes.append((len(raw),rel))
        if len(raw)>=95*1024*1024: issues.append({'path':rel,'rule':'file-over-95MiB'})
        for value in secrets:
            variants=[value.encode(),json.dumps(value)[1:-1].encode()]
            if any(v in raw for v in variants):
                issues.append({'path':rel,'rule':'matches-local-secret'}); break
        if re.search(rb'(?:ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}|sk-[A-Za-z0-9]{28,})',raw):
            issues.append({'path':rel,'rule':'provider-key-pattern'})
    return {'files':len(paths),'bytes':sum(n for n,_ in sizes),'largest':[{'path':p,'bytes':n} for n,p in sorted(sizes,reverse=True)[:12]],'issues':issues}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    paths=candidates()
    report=audit(paths)
    if not args.output:
        print(json.dumps(report,ensure_ascii=False,indent=2)); return
    if report['issues']:
        print(json.dumps(report,ensure_ascii=False,indent=2)); raise SystemExit('Resolve audit findings before copying')
    out=args.output.resolve()
    allowed=(ROOT/'提交材料/GitHub发布准备').resolve()
    if not out.is_relative_to(allowed) or out==allowed: raise SystemExit('Output must be a child of the dedicated release workspace')
    if out.exists(): raise SystemExit('Output already exists; use a fresh directory to preserve any commits')
    out.mkdir(parents=True)
    for path in paths:
        destination=out/path.relative_to(ROOT)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination)
    templates=ROOT/'scripts/github-release-templates'
    for path in templates.rglob('*'):
        if path.is_file():
            dest=out/path.relative_to(templates);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    # Config generation must use the release's own root, not this workstation's runtime.
    generated=[p for p in out.rglob('*') if p.is_file()]
    final=audit(generated)
    if final['issues']: raise SystemExit(json.dumps(final['issues'],ensure_ascii=False))
    final['remote']='https://github.com/luoye651-ye/sky-twin-ai.git'
    final['prepared_at']=datetime.now().isoformat(timespec='seconds')
    final['source_history']='current snapshot only; no reconstructed earlier project history'
    report_path=out.parent/'发布检查.json'
    report_path.write_text(json.dumps(final,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=[{'path':p.relative_to(out).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in generated]
    (out.parent/'文件清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'files':final['files'],'bytes':final['bytes'],'issues':final['issues'],'report':str(report_path)},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
