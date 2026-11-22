(() => {
  const e=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
  const main=document.querySelector('main'),header=main.querySelector('header'),audit=document.querySelector('#audit-panel');
  const nav=e('nav',undefined,'hub-nav');nav.setAttribute('aria-label','Dashboard sections');
  const radar=e('section');radar.id='radar-panel';
  const jobs=e('section');jobs.id='jobs-panel';
  for(const child of [...main.children])if(child!==header&&child!==audit)radar.append(child);
  main.append(nav,radar,audit,jobs);
  const pages=[['radar','Discovery',radar],['audit','Repo Auditor',audit],['jobs','Job Hunt',jobs]];
  const buttons=new Map();
  function activate(key){for(const [id,label,panel] of pages){const active=id===key;panel.hidden=!active;buttons.get(id).setAttribute('aria-current',active?'page':'false')}if(location.hash!=='#'+key)history.replaceState(null,'','#'+key)}
  for(const [key,label] of pages){const b=e('button',label,'hub-tab');b.type='button';b.onclick=()=>activate(key);buttons.set(key,b);nav.append(b)}
  activate(['radar','audit','jobs'].includes(location.hash.slice(1))?location.hash.slice(1):'radar');
  window.addEventListener('hashchange',()=>activate(['radar','audit','jobs'].includes(location.hash.slice(1))?location.hash.slice(1):'radar'));
  jobs.append(e('h2','Job Hunt'),e('p','Discover remote entry-level, support, automation, web and real estate roles. Check each employer’s actual location and experience requirements before applying.'));
  const links=e('div',undefined,'job-links');for(const [label,url] of [['OnlineJobs.ph','https://www.onlinejobs.ph/'],['Remote OK','https://remoteok.com/'],['Remotive','https://remotive.com/remote-jobs']]){const a=e('a',label);a.href=url;a.target='_blank';a.rel='noopener noreferrer';links.append(a)}jobs.append(links);
  const health=e('p','Loading public job feeds…','muted');health.setAttribute('role','status');jobs.append(health);
  const filters=e('div',undefined,'tools');const search=e('input');search.placeholder='Search jobs or companies';search.setAttribute('aria-label','Search jobs');
  function select(label,options){const s=e('select');s.setAttribute('aria-label',label);for(const [v,t] of options){const o=e('option',t);o.value=v;s.append(o)}return s}
  const category=select('Job category',[['','All roles'],...['Virtual assistant','Data & research','Automation','Web & tech','Real estate'].map(x=>[x,x])]);
  const locationFilter=select('Location eligibility',[['','All locations'],['Potential PH match','Potential PH match'],['Location unclear','Location unclear'],['Check region','Other region—check']]);
  const savedFilter=select('Application status',[['','All jobs'],['saved','Saved only'],['applied','Applied only']]);filters.append(search,category,locationFilter,savedFilter);jobs.append(filters);
  const count=e('p',undefined,'muted'),list=e('div',undefined,'job-list');jobs.append(count,list);
  let state={};try{state=JSON.parse(localStorage.getItem('radar-job-status-v1')||'{}')}catch(_){}
  let rows=[];function setStatus(url,value){if(value)state[url]=value;else delete state[url];try{localStorage.setItem('radar-job-status-v1',JSON.stringify(state))}catch(_){}render()}
  function render(){list.replaceChildren();const q=search.value.toLowerCase();const filtered=rows.filter(x=>(!category.value||x.categories.includes(category.value))&&(!locationFilter.value||x.eligibility===locationFilter.value)&&(!savedFilter.value||state[x.url]===savedFilter.value)&&[x.title,x.company,x.location,...x.categories].join(' ').toLowerCase().includes(q));count.textContent=filtered.length+' matching jobs · '+Object.values(state).filter(v=>v==='saved').length+' saved · '+Object.values(state).filter(v=>v==='applied').length+' marked applied';
    for(const x of filtered){const a=e('article',undefined,'job-card');const badges=e('div',undefined,'badges');badges.append(e('span',x.eligibility,'badge '+(x.eligibility==='Potential PH match'?'good':'')),e('span',x.source,'badge'));a.append(badges,e('h3',x.title),e('p',x.company,'company'),e('p',x.location+' · '+x.salary,'muted'),e('p',x.categories.join(' · ')+(x.posted?' · Posted '+x.posted.slice(0,10):''),'meta'));const actions=e('div',undefined,'card-actions');const link=e('a','View original job','primary-link');link.href=x.url;link.target='_blank';link.rel='noopener noreferrer';const save=e('button',state[x.url]==='saved'?'Saved ✓':'Save');save.onclick=()=>setStatus(x.url,state[x.url]==='saved'?'':'saved');const applied=e('button',state[x.url]==='applied'?'Applied ✓':'Mark applied');applied.onclick=()=>setStatus(x.url,state[x.url]==='applied'?'':'applied');actions.append(link,save,applied);a.append(actions);list.append(a)}if(!filtered.length)list.append(e('p','No matching jobs. Try a broader filter or visit a job board above.','empty'))}
  for(const f of [search,category,locationFilter,savedFilter])f.addEventListener('input',render);
  fetch('jobs.json?'+Date.now()).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{rows=d.jobs||[];const info=Object.entries(d.feeds||{}).map(([source,s])=>source+': '+(s.error?'feed unavailable; '+(s.last_success?'showing last successful results':'no cached results'):(s.last_success?'updated '+new Date(s.last_success).toLocaleString():'not yet fetched')));health.textContent=info.join(' | ')+' · Remotive listings may be delayed by 24 hours.';render()}).catch(()=>{health.textContent='Job feed results are not available yet. Use the direct job board links above.';render()});
})();
