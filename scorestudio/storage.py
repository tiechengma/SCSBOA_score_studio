"""Transactional local library and bounded, hash-checked exchange packages."""
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
import zipfile
import io
from datetime import datetime,timezone
from .model import SCHEMA,identity,validate,merge_records,school_key,school_name,DEFAULT_SCHOOL

MAX_PACKAGE=512*1024*1024
MAX_SOURCE=100*1024*1024
EXTENSIONS={'.pdf','.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff','.heic','.heif'}

class Library:
    def __init__(self,root):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.assets=self.root/'assets'; self.assets.mkdir(exist_ok=True)
        self.db=sqlite3.connect(self.root/'library.sqlite')
        self.db.execute('PRAGMA foreign_keys=ON'); self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS batches (id INTEGER PRIMARY KEY, label TEXT, created TEXT, before_state TEXT, after_count INTEGER);
        CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL);''')

    def default_school(self):
        row=self.db.execute("SELECT value FROM preferences WHERE key='default_school'").fetchone()
        return school_name(row[0]) if row else DEFAULT_SCHOOL

    def set_default_school(self,name):
        if not isinstance(name,str) or not name.strip() or len(name)>200:
            raise ValueError('Enter a school name (up to 200 characters).')
        with self.db:
            self.db.execute("INSERT INTO preferences VALUES('default_school',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(school_name(name),))

    @staticmethod
    def match_school_alias(record,current):
        """Match the known spelling alias without rewriting original saved school names."""
        key=identity(record)
        if key in current:return record
        matches=[old for old_key,old in current.items()
                 if old_key[:4]==key[:4] and school_key(old['school'])==school_key(record['school'])]
        if len(matches)==1:
            record=copy.deepcopy(record);record['school']=matches[0]['school']
        return record

    def update_awards(self,record,awards):
        before=self.records();after=copy.deepcopy(before)
        for row in after:
            if identity(row)==identity(record):
                row['awards']=copy.deepcopy(awards);validate(row)
                if before==after:return
                with self.db:
                    self.db.execute('INSERT INTO batches(label,created,before_state,after_count) VALUES(?,?,?,?)',
                        ('Awards · '+school_name(row['school']),datetime.now(timezone.utc).isoformat(),json.dumps(before),len(after)))
                    self.db.execute('UPDATE records SET body=? WHERE key=?',(json.dumps(row),json.dumps(identity(row))))
                return
        raise ValueError('This record is no longer in the library. Refresh and try again.')

    def records(self):
        return [json.loads(x[0]) for x in self.db.execute('SELECT body FROM records ORDER BY key')]

    def stage_source(self,path):
        path=Path(path)
        if path.suffix.lower() not in EXTENSIONS: raise ValueError('Unsupported source format.')
        if path.stat().st_size>MAX_SOURCE: raise ValueError('Source exceeds 100 MB. Split it first.')
        with path.open('rb') as stream:raw=stream.read(MAX_SOURCE+1)
        if len(raw)>MAX_SOURCE:raise ValueError('Source exceeds 100 MB. Split it first.')
        digest=hashlib.sha256(raw).hexdigest()
        name=digest+path.suffix.lower(); dest=self.assets/name
        self.write_asset(dest,io.BytesIO(raw))
        return {'asset':name,'name':path.name,'page':1,'sha256':digest}

    @staticmethod
    def hash_stream(stream):
        digest=hashlib.sha256();size=0
        while chunk:=stream.read(1024*1024):
            size+=len(chunk)
            if size>MAX_SOURCE:raise ValueError('Original attachment exceeds 100 MB.')
            digest.update(chunk)
        return digest.hexdigest()

    def asset_valid(self,path):
        try:
            with path.open('rb') as stream:return self.hash_stream(stream)==path.stem
        except (OSError,ValueError):return False

    def write_asset(self,dest,stream):
        if self.asset_valid(dest):return
        temp=dest.with_name(dest.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            digest=hashlib.sha256();size=0
            with temp.open('xb') as out:
                while chunk:=stream.read(1024*1024):
                    size+=len(chunk)
                    if size>MAX_SOURCE:raise ValueError('Original attachment exceeds 100 MB.')
                    out.write(chunk);digest.update(chunk)
                out.flush();os.fsync(out.fileno())
            if digest.hexdigest()!=dest.stem:raise ValueError('Attachment checksum mismatch.')
            os.replace(temp,dest)
        finally:
            if temp.exists():temp.unlink()

    def asset_path(self,source):
        name=source.get('asset','')
        if not isinstance(name,str) or not re.fullmatch(r'[0-9a-f]{64}\.[a-z0-9]+',name): raise ValueError('Invalid asset name.')
        if Path(name).suffix not in EXTENSIONS: raise ValueError('Invalid asset type.')
        return self.assets/name

    def preview(self,records):
        current={identity(r):r for r in self.records()}; counts={'new':0,'duplicate':0,'complement':0,'conflict':0}
        for r in records:
            validate(r);r=self.match_school_alias(r,current);old=current.get(identity(r))
            if old is None: counts['new']+=1; current[identity(r)]=r; continue
            union,conflicts=merge_records(old,r)
            status='conflict' if conflicts else ('duplicate' if union==old else 'complement')
            counts[status]+=1
            if not conflicts: validate(union);current[identity(r)]=union
        return counts

    def commit(self,records,label,resolver):
        current={identity(r):r for r in self.records()}; before=self.records();verified=set()
        for row in records:
            r=copy.deepcopy(row); validate(r);r=self.match_school_alias(r,current)
            for src in r['sources']:
                asset=self.asset_path(src)
                if asset not in verified:
                    if not self.asset_valid(asset):raise ValueError('Missing or damaged original: '+src['name']+'. Reimport the original or a valid package.')
                    verified.add(asset)
            key=identity(r); old=current.get(key)
            if old:
                merged,conflicts=merge_records(old,r)
                if conflicts:
                    # Resolver supplies an explicit choice per field, or cancels entire batch.
                    choices=resolver(old,r,conflicts)
                    if choices is None: return False
                    for category,field,prev,value in conflicts:
                        if choices.get((category,field)) not in ('incoming','saved'):
                            raise ValueError('Choose every conflicting field explicitly.')
                        if choices.get((category,field))=='incoming':
                            if category=='record':merged=copy.deepcopy(r)
                            elif category=='metadata': merged[field]=value
                            else: merged[category][field]=value
                validate(merged)
                current[key]=merged
            else: current[key]=r
        after=list(current.values())
        for row in after:validate(row)
        if after==before: return True
        with self.db:
            self.db.execute('INSERT INTO batches(label,created,before_state,after_count) VALUES(?,?,?,?)',
                (label,datetime.now(timezone.utc).isoformat(),json.dumps(before),len(after)))
            self.db.execute('DELETE FROM records')
            self.db.executemany('INSERT INTO records VALUES(?,?)',[(json.dumps(identity(r)),json.dumps(r)) for r in after])
        return True

    def history(self):
        return list(self.db.execute('SELECT id,label,created,after_count FROM batches ORDER BY id DESC'))

    def undo(self):
        row=self.db.execute('SELECT id,before_state FROM batches ORDER BY id DESC LIMIT 1').fetchone()
        if not row: return False
        with self.db:
            self.db.execute('DELETE FROM records')
            for r in json.loads(row[1]): self.db.execute('INSERT INTO records VALUES(?,?)',(json.dumps(identity(r)),json.dumps(r)))
            self.db.execute('DELETE FROM batches WHERE id=?',(row[0],))
        return True

    def export_package(self,path,records=None):
        records=self.records() if records is None else records
        if len(records)>50000:raise ValueError('Export exceeds 50,000 records. Split it by season.')
        for row in records:validate(row)
        manifest={'format':'scsboa-score-studio','version':SCHEMA,'created':datetime.now(timezone.utc).isoformat(),'records':records}
        manifest_bytes=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf8')
        if len(manifest_bytes)>20*1024*1024:raise ValueError('Export manifest exceeds 20 MB. Split it by season.')
        path=Path(path); temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('manifest.json',manifest_bytes)
                names=set();total=len(manifest_bytes)
                for r in records:
                    for src in r['sources']:
                        name=src['asset']
                        if name not in names:
                            asset=self.asset_path(src)
                            if not asset.is_file(): raise ValueError('Missing original: '+src['name'])
                            with asset.open('rb') as stream:raw=stream.read(MAX_SOURCE+1)
                            if len(raw)>MAX_SOURCE or hashlib.sha256(raw).hexdigest()!=asset.stem:
                                raise ValueError('Damaged or oversized original: '+src['name']+'. Reimport it before exporting.')
                            total+=len(raw)
                            if total>MAX_PACKAGE or len(names)>=9999:raise ValueError('Export package is too large. Split it by season.')
                            z.writestr('assets/'+name,raw); names.add(name)
            os.replace(temp,path)
        finally:
            if temp.exists(): temp.unlink()

    def read_package(self,path):
        with zipfile.ZipFile(path) as z:
            infos=z.infolist(); names=[i.filename for i in infos]
            if len(infos)>10000 or sum(i.file_size for i in infos)>MAX_PACKAGE or len(set(names))!=len(names):
                raise ValueError('Package is too large or has duplicate entries.')
            if 'manifest.json' not in names or z.getinfo('manifest.json').file_size>20*1024*1024:
                raise ValueError('Missing or oversized manifest.')
            m=json.loads(z.read('manifest.json'))
            if not isinstance(m,dict) or m.get('format')!='scsboa-score-studio' or type(m.get('version')) is not int or m.get('version') not in (1,SCHEMA):
                raise ValueError('Unsupported package version.')
            rows=m.get('records')
            if not isinstance(rows,list) or len(rows)>50000: raise ValueError('Invalid record list.')
            checked={}
            for r in rows:
                validate(r)
                for src in r['sources']:
                    dest=self.asset_path(src); name='assets/'+dest.name
                    if name not in names: raise ValueError('Package is missing an original attachment.')
                    if name not in checked:
                        if z.getinfo(name).file_size>MAX_SOURCE:raise ValueError('Original attachment exceeds 100 MB.')
                        with z.open(name) as stream:digest=self.hash_stream(stream)
                        if digest!=dest.stem: raise ValueError('Attachment checksum mismatch.')
                        checked[name]=dest
            # Never extract arbitrary archive paths; only content-addressed allowlisted assets.
            for name,dest in checked.items():
                with z.open(name) as stream:self.write_asset(dest,stream)
            return rows
