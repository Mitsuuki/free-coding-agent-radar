"""Public discovery feeds only. No downloads, execution, or AI credentials."""
import base64, json, os, re, urllib.request, urllib.parse, datetime as dt
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent / 'docs'
NOW = dt.datetime.now(dt.timezone.utc).isoformat()
rows, errors = {}, []
def get(url, github=False):
    headers = {'User-Agent': 'FreeCodingRadar/1.0', 'Accept': 'application/json'}
    if github and os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as response:
        return response.read().decode()
def add(title, url, source, description='', date='', stars=0):
    if not url.startswith(('https://','http://')): return
    text = (title + ' ' + description).lower()
    if re.search(r'\b(exploit|malware|phishing|cracking|bypass|hacking)\b', text): return
    score = sum(w in text for w in ['coding agent','free','open source','cli','code','agent','inference','api','model'])
    if score < 2: return
    rows[url] = dict(title=title[:250], url=url, source=source, description=description[:650], date=date, stars=stars, score=score, status='Unverified lead')
def attempt(name, fn):
    try: fn()
    except Exception as e: errors.append({'source':name,'error':str(e)[:200]})
def github():
    for query in ['"coding agent" in:name,description,readme archived:false stars:>10','"free" "coding agent" in:description,readme archived:false stars:>5','"free llm" in:name,description archived:false stars:>10']:
        params=urllib.parse.urlencode({'q':query,'sort':'updated','per_page':30})
        data=json.loads(get('https://api.github.com/search/repositories?'+params,True))
        for item in data.get('items',[]): add(item['full_name'],item['html_url'],'GitHub',item.get('description') or '',item.get('pushed_at',''),item.get('stargazers_count',0))
def hn():
    for query in ['free coding agent','open source coding agent','free LLM API']:
        params=urllib.parse.urlencode({'query':query,'tags':'story','hitsPerPage':25})
        for x in json.loads(get('https://hn.algolia.com/api/v1/search_by_date?'+params)).get('hits',[]):
            add(x.get('title') or '', 'https://news.ycombinator.com/item?id='+x['objectID'],'Hacker News',x.get('story_text') or '',x.get('created_at',''))
def reddit():
    for sub in ['LocalLLaMA','ChatGPTCoding','opensource']:
        try:
            q=urllib.parse.urlencode({'q':'free coding agent','restrict_sr':'on','sort':'new'})
            root=ET.fromstring(get('https://www.reddit.com/r/'+sub+'/search.rss?'+q))
            ns={'a':'http://www.w3.org/2005/Atom'}
            for x in root.findall('a:entry',ns):
                link=x.find('a:link',ns)
                if link is not None: add(x.findtext('a:title','',ns),link.get('href',''),'Reddit', '',x.findtext('a:updated','',ns))
        except Exception as e: errors.append({'source':'Reddit r/'+sub,'error':str(e)[:200]})
WATCH = {
    'jordan-gibbs/hyperresearch': 'Research harness; requires compatible agent/model access. Not executed.',
    'cporter202/API-mega-list': 'API directory; source for prospective provider leads.',
    'cporter202/agentic-ai-apis': 'Agent and model API directory; listed services may be paid or affiliate-linked.',
    'elie222/rakazo': 'Agent framework candidate; not needed for the free scheduled scanner.',
    'Tencent/WeKnora': 'Knowledge-base candidate; requires its own deployment and model configuration.',
    'yetone/magpie': 'Provider connectivity candidate; not installed and no credentials imported.',
    'mvalentsev/awesome-free-ai-coding': 'Maintained free AI coding directory; independently verify its claims.'
}
def watch_repo(repo, note):
    x=json.loads(get('https://api.github.com/repos/'+repo, True))
    url=x['html_url']
    rows[url]=dict(title=repo,url=url,source='Watchlist',description=note+' '+(x.get('description') or '')[:400],date=x.get('pushed_at',''),stars=x.get('stargazers_count',0),score=8,status='Tracked repository; not installed')
def directory_readme(repo,path=''):
    endpoint='https://api.github.com/repos/'+repo+'/readme'
    if path: endpoint='https://api.github.com/repos/'+repo+'/contents/'+urllib.parse.quote(path)
    x=json.loads(get(endpoint,True))
    if x.get('encoding')!='base64': return
    contents=base64.b64decode(x['content']).decode('utf-8','replace')
    for index,line in enumerate(contents.splitlines(),1):
        lower=line.lower()
        if not re.search(r'\b(free|no.card|zero.cost)\b',lower): continue
        if not re.search(r'\b(coding|agent|llm|inference|model|api)\b',lower): continue
        match=re.search(r'\[([^\]]{2,100})\]\(https?://[^)]+\)',line)
        if not match: continue
        # Link only to the directory evidence; never follow arbitrary provider links automatically.
        add(match.group(1), x['html_url']+'#L'+str(index),'Curated directory',line,'')
def directory(repo):
    directory_readme(repo)
    if repo.startswith('cporter202/'):
        root=json.loads(get('https://api.github.com/repos/'+repo+'/contents',True))
        for item in root:
            name=item.get('name','')
            if item.get('type')=='dir' and re.match(r'^(agents?|ai-models|ai-apis|developer-tools-apis)(-|$)',name.lower()):
                attempt(repo+'/'+name, lambda n=name: directory_readme(repo,n+'/README.md'))
for name, fn in [('GitHub',github),('Hacker News',hn),('Reddit',reddit)]: attempt(name,fn)
for repo,note in WATCH.items(): attempt(repo,lambda r=repo,n=note:watch_repo(r,n))
for repo in ['cporter202/API-mega-list','cporter202/agentic-ai-apis','mvalentsev/awesome-free-ai-coding']:
    attempt(repo+' directory',lambda r=repo:directory(r))
path=ROOT/'results.json'
previous=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'leads':[]}
old={x['url']:x for x in previous['leads']}
for url,row in rows.items():
    row['first_seen']=old.get(url,{}).get('first_seen',NOW)
    row['last_seen']=NOW
    old[url]=row
leads=sorted(old.values(),key=lambda x:(x.get('last_seen',''),x['score'],x.get('stars',0)),reverse=True)[:500]
path.write_text(json.dumps({'scanned':NOW,'new':sum(url not in {x['url'] for x in previous['leads']} for url in rows),'errors':errors,'leads':leads},indent=2),encoding='utf-8')
print(f'{len(rows)} leads; {len(errors)} source errors')
