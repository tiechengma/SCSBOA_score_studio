"""Versioned, UI-independent records and merge rules."""
import copy
import math
import re
from datetime import date

SCHEMA = 2
DEFAULT_SCHOOL = 'Arroyo Knight Band & Colorguard'
SCHOOL_ALIASES = {DEFAULT_SCHOOL.casefold(), 'arroyo knights band & colorguard'}
# A key describes a printed column, not an inferred global scoring rule.
COLUMNS = [
 ('music.j1.stt','Music · Judge 1 · STT'),('music.j1.mus','Music · Judge 1 · MUS'),
 ('music.j1.total','Music · Judge 1 · Total'),('music.j2.stt','Music · Judge 2 · STT'),
 ('music.j2.mus','Music · Judge 2 · MUS'),('music.j2.total','Music · Judge 2 · Total'),
 ('music.total','Music · Total'),('ge.j1.comp','GE · Judge 1 · COMP EFF'),
 ('ge.j1.comm','GE · Judge 1 · COMM EFF'),('ge.j1.total','GE · Judge 1 · Total'),
 ('ge.j2.comp','GE · Judge 2 · COMP EFF'),('ge.j2.comm','GE · Judge 2 · COMM EFF'),
 ('ge.j2.total','GE · Judge 2 · Total'),('ge.total','GE · Total'),
 ('visual.comp','Visual · VIS COMP'),('visual.exc','Visual · EXC'),('visual.total','Visual · Total'),
 ('subtotal','Subtotal'),('penalties.raw','Penalties · PEN'),('penalties.total','Penalties · Total'),
 ('total','Final total'),('auxiliary.comp','Auxiliary · COMP'),('auxiliary.ach','Auxiliary · ACH'),
 ('auxiliary.raw','Auxiliary · Raw total'),('auxiliary.total','Auxiliary · Factored total'),
 ('percussion.comp','Percussion · COMP'),('percussion.ach','Percussion · ACH'),
 ('percussion.raw','Percussion · Raw total'),('percussion.total','Percussion · Factored total')]
LABELS = dict(COLUMNS)
MAIN = ['total','music.total','ge.total','visual.total','auxiliary.total','percussion.total']
CAPTIONS = {'total':'Overall','music.total':'Music','ge.total':'General Effect',
            'visual.total':'Visual','auxiliary.total':'Auxiliary','percussion.total':'Percussion'}

def normalized(s):
    return re.sub(r'\s+', ' ', str(s).strip()).casefold()

def school_name(s):
    return DEFAULT_SCHOOL if normalized(s) in SCHOOL_ALIASES else str(s).strip()

def school_key(s):
    return normalized(school_name(s))

def leaders(records,metric):
    """Source rank takes precedence; an incomplete import never invents first place."""
    first=[r for r in records if r.get('ranks',{}).get(metric)==1]
    if first:return 'source',first
    available=[r for r in records if r.get('scores',{}).get(metric) is not None]
    if not available:return 'missing',[]
    top=max(r['scores'][metric] for r in available)
    return 'imported',[r for r in available if abs(r['scores'][metric]-top)<1e-9]

def validate_awards(awards):
    if not isinstance(awards,dict) or len(awards)>100:
        raise ValueError('Awards must be a list of up to 100 named awards with source notes.')
    seen=set()
    for name,evidence in awards.items():
        if not isinstance(name,str) or not name.strip() or len(name)>200:
            raise ValueError('Each award needs a name (up to 200 characters).')
        if not isinstance(evidence,str) or not evidence.strip() or len(evidence)>2000:
            raise ValueError('Each award needs a source note (up to 2000 characters).')
        if normalized(name) in seen:raise ValueError('Duplicate award name.')
        seen.add(normalized(name))

def identity(r):
    return tuple(normalized(r.get(k,'')) for k in ('season','date','event','division','school'))

def blank_record():
    return dict(season='2026',date='',event='',division='',school='',original_school='',
                scheme='scsboa-field-2026',scores={},ranks={},judges={},sources=[],notes='',awards={})

def number(value):
    if value is None or str(value).strip() == '':
        return None
    n=float(value)
    if not math.isfinite(n) or abs(n)>10000:
        raise ValueError('Scores must be finite numbers between -10000 and 10000.')
    return n

def validate(r):
    if not isinstance(r,dict):raise ValueError('Each record must be an object.')
    validate_awards(r.get('awards',{}))
    for key in ('season','date','event','division','school','scheme'):
        if not isinstance(r.get(key),str) or not r[key].strip():
            raise ValueError(f'{key.title()} is required.')
    date.fromisoformat(r['date'])
    if not re.fullmatch(r'\d{4}',r['season']):
        raise ValueError('Season must be a four-digit year.')
    for category in ('scores','ranks'):
        if not isinstance(r.get(category),dict):
            raise ValueError(f'Invalid {category}.')
        for key,value in r[category].items():
            if key not in LABELS:
                raise ValueError(f'Unsupported score field: {key}')
            if value is not None and type(value) not in (int,float):
                raise ValueError(f'{category}.{key}: expected a number or null, not text or a boolean.')
            n=number(value)
            if category=='ranks' and n is not None and (n<1 or int(n)!=n):
                raise ValueError('Ranks must be positive whole numbers.')
    if not isinstance(r.get('sources'),list) or not isinstance(r.get('judges'),dict):
        raise ValueError('Invalid source or judge metadata.')
    for key,value in r['judges'].items():
        if not isinstance(key,str) or not isinstance(value,str):raise ValueError('Judge names must be text.')
    for key in ('notes','original_school','header_text'):
        if key in r and not isinstance(r[key],str):raise ValueError(f'{key} must be text.')
    for src in r['sources']:
        if not isinstance(src,dict) or not isinstance(src.get('name'),str) or type(src.get('page')) is not int or not 1<=src['page']<=100:
            raise ValueError('Source must have a filename and page between 1 and 100.')

def warnings(r):
    s=r['scores']; issues=[]
    for key,title in COLUMNS:
        if s.get(key) is None:
            issues.append(f'Missing {LABELS[key]}')
    if r.get('date','')[:4] and r.get('date','')[:4]!=r.get('season'):
        issues.append('Event year differs from selected season')
    equations=[('music.j1.total',['music.j1.stt','music.j1.mus']),
      ('music.j2.total',['music.j2.stt','music.j2.mus']),
      ('music.total',['music.j1.total','music.j2.total']),
      ('ge.j1.total',['ge.j1.comp','ge.j1.comm']),('ge.j2.total',['ge.j2.comp','ge.j2.comm']),
      ('ge.total',['ge.j1.total','ge.j2.total']),('visual.total',['visual.comp','visual.exc']),
      ('subtotal',['music.total','ge.total','visual.total']),
      ('auxiliary.raw',['auxiliary.comp','auxiliary.ach']),('percussion.raw',['percussion.comp','percussion.ach'])]
    for total,parts in equations:
        if s.get(total) is not None and all(s.get(k) is not None for k in parts):
            if abs(s[total]-sum(s[k] for k in parts))>.015:
                issues.append(f'Check sum: {LABELS[total]} (factoring may apply)')
    if all(s.get(k) is not None for k in ['subtotal','total','penalties.total']):
        if abs(s['subtotal']-abs(s['penalties.total'])-s['total'])>.015:
            issues.append('Check subtotal / penalty / final total')
    for key,value in s.items():
        if value is not None and value<0 and not key.startswith('penalties'):
            issues.append(f'Negative score: {LABELS[key]}')
    return issues

def merge_records(old,new):
    """Return complementary union + explicit field conflicts, never overwrite silently."""
    if old.get('scheme')!=new.get('scheme'):
        return copy.deepcopy(old),[('record','scheme',old.get('scheme'),new.get('scheme'))]
    merged=copy.deepcopy(old); conflicts=[]
    for category in ('scores','ranks','judges','awards'):
        if category not in old and not new.get(category):continue
        merged.setdefault(category,{})
        for key,value in new.get(category,{}).items():
            if value is None or value=='': continue
            if category=='awards':
                key=next((saved for saved in merged[category] if normalized(saved)==normalized(key)),key)
            prev=merged[category].get(key)
            if prev is None or prev=='': merged[category][key]=value
            elif prev!=value: conflicts.append((category,key,prev,value))
    for src in new.get('sources',[]):
        if src not in merged['sources']: merged['sources'].append(copy.deepcopy(src))
    for key in ('notes','original_school'):
        if not merged.get(key): merged[key]=new.get(key,'')
    return merged,conflicts
