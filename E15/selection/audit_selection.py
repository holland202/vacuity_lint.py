#!/usr/bin/env python3
"""Audit an E15 v2 selection run against PREREG_v2.md. Usage: python audit_selection.py E15/selection/run"""
import os, sys
os.chdir(sys.argv[1] if len(sys.argv) > 1 else ".")
import json, re, sys, collections
def body(path):
    t=open(path,encoding='utf-8').read()
    hdr=t.split('\n')[:4]
    status=re.search(r'^HTTP/\S+ (\d+)', t, re.M).group(1)
    i=t.find('\n{') if '\n{' in t else t.find('\n[')
    j=min([k for k in (t.find('\n{'), t.find('\n[')) if k>=0])
    b=t[j+1:].split('\n# stderr:')[0]
    return hdr, status, json.loads(b), t
REG="language:Python stars:5..50 pushed:>2025-09-08 fork:false archived:false"
out=[]; bad=0
def chk(ok,msg):
    global bad; bad+= not ok; out.append(("PASS" if ok else "FAIL")+"  "+msg)
hdr,st,pg,t=body('raw/search_page_001.txt')
chk(st=='200', f"search page HTTP {st}")
chk(f"q={REG}" in hdr[1], "raw command carries the registered query verbatim")
chk('sort=stars' in hdr[1] and 'order=desc' in hdr[1] and 'per_page=100' in hdr[1], "sort=stars, order=desc, per_page=100")
items=[i['full_name'] for i in pg['items']]
sel=json.load(open('selection.json'))
chk([r['full_name'] for r in sel]==items[:len(sel)], f"selection order == API return order for all {len(sel)} records")
stars=[i['stargazers_count'] for i in pg['items'][:len(sel)]]
chk(all(5<=s<=50 for s in stars) and stars==sorted(stars,reverse=True), f"stars in 5..50 and descending ({stars[0]}..{stars[-1]})")
chk(all(not i['fork'] and not i['archived'] for i in pg['items'][:len(sel)]), "no forks or archived repos among processed items")
def rule(r, owner_check=True):
    if not r.get('clone_ok'): return 3
    n=r['py_files']
    if n<5: return 1
    if n>2000: return 2
    if owner_check and r['owner'].lower()=='holland202': return 4
    return None
chk(all(r['failed_rule']==rule(r) and r['eligible']==(rule(r) is None) for r in sel), "every pool eligibility verdict matches its recorded clone/py count/owner")
ci_ok=all((r['arm']=='C')==bool(r['ci_paths']) for r in sel if r['eligible'])
chk(ci_ok, "every eligible pool repo's arm matches its recorded CI paths")
b=c=0; first_both=None
for k,r in enumerate(sel):
    if r['eligible']:
        b+=r['arm']=='B'; c+=r['arm']=='C'
    if b>=20 and c>=20 and first_both is None: first_both=k
chk(first_both==len(sel)-1, f"stopped at the first record where both strata hit 20 (record {first_both+1} of {len(sel)})")
chk(sum(1 for r in sel if r.get('duplicate_in_results'))==0, "no duplicate repos in the processed results")
fails=collections.Counter(r['failed_rule'] for r in sel if not r['eligible'])
out.append(f"INFO  ineligible pool repos by rule: {dict(fails)}")
for r in sel:
    if r['failed_rule']==3: out.append(f"INFO  clone failure: order {r['order']} after {r['clone_seconds']}s: {r.get('clone_error','')[:90]}")
listing=[]
import glob
for p in sorted(glob.glob('raw/arm_a_page_*.txt')):
    h,s,bd,_=body(p); chk(s=='200', f"{p} HTTP {s}"); listing+=bd
pub=[x['full_name'] for x in listing if not x.get('private')]
aa=json.load(open('arm_a.json'))
chk(sorted(pub)==sorted(r['full_name'] for r in aa), f"Arm A covers every public holland202 repo listed ({len(pub)})")
chk(all(r['failed_rule']==rule(r,False) and r['eligible']==(rule(r,False) is None) for r in aa), "every Arm A verdict matches rules 1-3")
af=collections.Counter(r['failed_rule'] for r in aa if not r['eligible'])
out.append(f"INFO  Arm A: {sum(r['eligible'] for r in aa)} eligible of {len(aa)}; ineligible by rule {dict(af)}; forks among eligible: {sum(1 for r in aa if r['eligible'] and r['fork'])}; archived among eligible: {sum(1 for r in aa if r['eligible'] and r['archived'])}")
allraw=''.join(open(p,encoding='utf-8').read() for p in glob.glob('raw/*.txt'))+open('../run_console.log').read()
chk(not re.search(r'gh[opsu]_[A-Za-z0-9]{20,}|[Aa]uthorization:', allraw), "no tokens or Authorization headers in committed raw files or console log")
chk(all(r.get('commit') and len(r['commit'])==40 for r in sel+aa if r['eligible']), "every eligible repo has its exact 40-char commit recorded")
print('\n'.join(out)); print(f"\n{sum(o.startswith(('PASS','FAIL')) for o in out)-bad} passed, {bad} failed")
sys.exit(1 if bad else 0)
