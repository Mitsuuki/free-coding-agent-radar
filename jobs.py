"""Public remote job feeds; no account, scraping, applications or personal data."""
import datetime as dt, json, re, urllib.request, urllib.parse
from pathlib import Path

ROOT=Path(__file__).parent/'docs'; NOW=dt.datetime.now(dt.timezone.utc)
FEEDS={'Remote OK':'https://remoteok.com/api','Remotive':'https://remotive.com/api/remote-jobs'}
KEYS={'Virtual assistant':['virtual assistant','administrative assistant','executive assistant','admin assistant','operations assistant','customer support','customer service'],
      'Data & research':['data entry','data annotation','research assistant','data assistant','data processing','data quality'],
      'Automation':['n8n','automation specialist','workflow automation','zapier','make.com','automation assistant','no-code'],
      'Web & tech':['junior developer','junior web','web developer','frontend developer','front-end developer','wordpress','website assistant','technical support','software intern'],
      'Real estate':['real estate assistant','property management','property assistant','leasing assistant','real estate virtual assistant','property coordinator']}
def parse_date(value):
    try:
        d=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (TypeError,ValueError): return None
def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'FreeCodingRadarJobDiscovery/1.0','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as r:
        data=r.read(10_000_001)
        if len(data)>10_000_000: raise ValueError('Feed exceeded size limit')
        return json.loads(data)
def classify(title,tags):
    text=(title+' '+' '.join(tags)).lower(); matches=[key for key,words in KEYS.items() if any(w in text for w in words)]
    if re.search(r'\b(senior|staff|principal|director|lead|head of|manager|architect)\b',title,re.I) and not re.search(r'property management',title,re.I): return []
    return matches
def eligibility(loc):
    text=loc.lower()
    if any(s in text for s in ['philippines','worldwide','anywhere','global','asia','apac']): return 'Potential PH match'
    if not text.strip() or text.strip() in ['remote','unknown']: return 'Location unclear'
    return 'Check region'
def pick(source,raw):
    if source=='Remotive': raw=raw.get('jobs',[])
    out=[]
    for x in raw:
        if not isinstance(x,dict): continue
        title=str(x.get('title') or x.get('position') or '')[:200]; company=str(x.get('company_name') or x.get('company') or '')[:150]
        tags=x.get('tags') or []; tags=[str(t) for t in tags][:30] if isinstance(tags,list) else []
        cat=classify(title,tags)
        if not title or not company or not cat: continue
        url=str(x.get('url') or ''); parsed=urllib.parse.urlparse(url)
        allowed={'remotive.com','www.remotive.com'} if source=='Remotive' else {'remoteok.com','www.remoteok.com','remoteok.io','www.remoteok.io'}
        if parsed.scheme!='https' or parsed.hostname not in allowed: continue
        loc=str(x.get('candidate_required_location') or x.get('location') or '')[:180]; posted=str(x.get('publication_date') or x.get('date') or '')[:50]
        sal=str(x.get('salary') or '')[:140]
        if not sal and x.get('salary_min') and x.get('salary_max'): sal=f"{x['salary_min']}–{x['salary_max']} (units per listing)"
        date=parse_date(posted)
        if date and NOW-date>dt.timedelta(days=30): continue
        out.append({'title':title,'company':company,'url':url,'source':source,'location':loc or 'Not stated','eligibility':eligibility(loc),'categories':cat,'posted':posted,'salary':sal or 'Not stated','kind':str(x.get('job_type') or '')[:80]})
    return out
def main():
    path=ROOT/'jobs.json'; previous=json.loads(path.read_text()) if path.exists() else {'feeds':{}}; feeds=previous.get('feeds',{})
    for source,url in FEEDS.items():
        state=feeds.get(source,{}); last=parse_date(state.get('last_attempt'))
        # Both feeds are refreshed at most once per six hours (Remotive recommends <=4/day).
        if last and NOW-last<dt.timedelta(hours=6): continue
        state['last_attempt']=NOW.isoformat()
        try:
            state['jobs']=pick(source,fetch(url));state['last_success']=NOW.isoformat();state['error']=None
        except Exception as e: state['error']=str(e)[:180]
        feeds[source]=state
    items={}
    for state in feeds.values():
        for job in state.get('jobs',[]): items[job['url']]=job
    jobs=sorted(items.values(),key=lambda x:({'Potential PH match':2,'Location unclear':1,'Check region':0}[x['eligibility']],x['posted']),reverse=True)[:300]
    path.write_text(json.dumps({'updated':NOW.isoformat(),'feeds':feeds,'jobs':jobs},indent=2),encoding='utf-8')
    print('Job leads:',len(jobs),'feed errors:',sum(bool(x.get('error')) for x in feeds.values()))
if __name__=='__main__':main()
