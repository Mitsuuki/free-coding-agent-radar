"""Read-only software supply-chain triage of public GitHub repositories.

No target checkout, execution, network probing, or vulnerability reproduction.
Only public metadata and root dependency manifests are inspected.
"""
import base64, datetime as dt, json, os, re, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent / 'docs'
NOW = dt.datetime.now(dt.timezone.utc)
PRIORITY = ['CodebuffAI/freebuff','happier-dev/happier','susomejias/rembric',
            'backnotprop/plannotator','wanderingstan/vibeconf-app','elie222/rakazo',
            'yetone/magpie','Tencent/WeKnora','Graphify-Labs/graphify',
            'alibaba/open-code-review','jordan-gibbs/hyperresearch',
            'mvalentsev/awesome-free-ai-coding']
REPO = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
VERSION = re.compile(r'^\d+(?:\.\d+){1,3}(?:[-+][A-Za-z0-9.]+)?$')

def request(url, payload=None):
    headers={'User-Agent':'RadarSupplyChainReview/1.0','Accept':'application/json'}
    if url.startswith('https://api.github.com/') and os.getenv('GITHUB_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    body=None
    if payload is not None:
        headers['Content-Type']='application/json'; body=json.dumps(payload).encode()
    with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=headers),timeout=12) as resp:
        raw=resp.read(2_000_001)
        if len(raw)>2_000_000: raise ValueError('Response exceeds review size limit')
        return json.loads(raw)

def manifest(base, filename):
    item=request(base+'/contents/'+filename)
    if item.get('type')!='file' or item.get('encoding')!='base64': raise ValueError('Manifest unavailable')
    return base64.b64decode(item['content']).decode('utf-8','replace')

def audit(repo):
    base='https://api.github.com/repos/'+repo
    result={'repo':repo,'url':'https://github.com/'+repo,'checked':NOW.isoformat(),
            'status':'Unassessed','notes':[],'checks':{},'errors':[]}
    checks=result['checks']; notes=result['notes']; errors=result['errors']
    try:
        meta=request(base); checks['license']=(meta.get('license') or {}).get('spdx_id') or 'Not detected'
        checks['last_push']=meta.get('pushed_at'); checks['archived']=bool(meta.get('archived')); checks['stars']=meta.get('stargazers_count',0)
        if checks['archived']: notes.append('Repository is archived.')
        if checks['license'] in ('Not detected','NOASSERTION'): notes.append('License needs manual review.')
        if checks['last_push'] and NOW-dt.datetime.fromisoformat(checks['last_push'].replace('Z','+00:00'))>dt.timedelta(days=180): notes.append('No recorded push in the past 180 days.')
    except Exception as e: errors.append('Metadata unavailable: '+str(e)); return result
    try:
        files=request(base+'/contents'); names={f['name'] for f in files if f.get('type')=='file'}; checks['root_files']=len(files)
        checks['security_policy_root']='SECURITY.md' in names
        checks['dependency_manifests']=sorted(names.intersection({'package.json','package-lock.json','requirements.txt','pyproject.toml','poetry.lock','uv.lock','Cargo.toml','Cargo.lock','go.mod','go.sum','pnpm-lock.yaml','yarn.lock'}))
        checks['install_script_names']=sorted(n for n in names if re.match(r'^(install|setup|bootstrap)(\.|$)',n,re.I))
        if checks['install_script_names']: notes.append('Review installer scripts before running them.')
    except Exception as e: errors.append('Root listing unavailable: '+str(e)); return result
    queries=[]; seen=set(); skipped=0
    def add_dependency(name,version,ecosystem):
        nonlocal skipped
        if not isinstance(version,str) or not VERSION.fullmatch(version): skipped+=1; return
        key=(name,version,ecosystem)
        if key not in seen:
            seen.add(key); queries.append({'package':{'name':name,'ecosystem':ecosystem},'version':version})
    try:
        if 'package.json' in names:
            package=json.loads(manifest(base,'package.json'))
            checks['npm_lifecycle_hooks']=sorted(set((package.get('scripts') or {}).keys()).intersection({'preinstall','install','postinstall','prepare'}))
            if checks['npm_lifecycle_hooks']: notes.append('npm install lifecycle hooks are declared; inspect before installation.')
            for group in ['dependencies','devDependencies','optionalDependencies']:
                for name,version in (package.get(group) or {}).items(): add_dependency(name,version,'npm')
        if 'requirements.txt' in names:
            for line in manifest(base,'requirements.txt').splitlines():
                pin=re.fullmatch(r'\s*([A-Za-z0-9_.-]+)==(\S+)\s*',line)
                if pin: add_dependency(pin.group(1),pin.group(2),'PyPI')
                elif line.strip() and not line.lstrip().startswith('#'): skipped+=1
    except Exception as e: errors.append('Manifest review incomplete: '+str(e))
    checks['exact_pins_found']=len(queries); checks['unresolved_entries']=skipped
    checks['pins_checked']=0; checks['known_advisory_matches']=None
    if queries:
        try:
            batch=request('https://api.osv.dev/v1/querybatch',{'queries':queries[:40]})['results']
            if len(batch)!=min(len(queries),40): raise ValueError('Incomplete advisory response')
            checks['pins_checked']=len(batch); checks['known_advisory_matches']=sum(bool(x.get('vulns')) for x in batch)
            if checks['known_advisory_matches']: notes.append('Published advisories match one or more checked dependency versions; review upgrades before use.')
            if any(x.get('next_page_token') for x in batch): errors.append('Advisory results paginated; review incomplete.')
        except Exception as e: errors.append('OSV lookup unavailable: '+str(e))
    if not checks['pins_checked']: notes.append('No exact dependency versions checked; lockfiles and transitive dependencies are not covered.')
    if skipped or len(queries)>40: notes.append('Some dependency entries were outside the supported or bounded review.')
    result['status']='Review required' if notes or errors else 'Limited checks completed'
    return result

def main():
    path=ROOT/'audits.json'; old=json.loads(path.read_text()) if path.exists() else {'audits':[]}
    prior={x['repo'].lower():x for x in old['audits']}
    leads=json.loads((ROOT/'results.json').read_text()).get('leads',[])
    names=list(PRIORITY)
    for x in leads:
        name=x.get('title',''); desc=x.get('description','').lower()
        if x.get('source') in ('GitHub','Watchlist') and REPO.fullmatch(name) and not re.search(r'\b(exploit|malware|offensive|phishing|hacking|vulnerability scanner|bypass)\b',desc): names.append(name)
    names=list({n.lower():n for n in names}.values())
    names.sort(key=lambda n:(prior.get(n.lower(),{}).get('checked',''),n not in PRIORITY))
    # Bound every run; oldest/unreviewed records first.
    with ThreadPoolExecutor(max_workers=3) as pool:
        for item in pool.map(audit,names[:12]): prior[item['repo'].lower()]=item
    path.write_text(json.dumps({'updated':NOW.isoformat(),'eligible':len(names),'audits':list(prior.values())},indent=2),encoding='utf-8')
    print('Audited',min(12,len(names)),'public repositories (limited evidence)')

if __name__=='__main__': main()
