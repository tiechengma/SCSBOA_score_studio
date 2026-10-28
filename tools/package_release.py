"""Copy dependency notices and docs alongside an already verified portable build."""
import importlib.metadata as metadata
from pathlib import Path
import shutil
import sys
import zipfile

root=Path(__file__).resolve().parents[1]
release_root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'dist'
dist=release_root/'SCSBOA-Score-Studio';licenses=dist/'licenses';licenses.mkdir(exist_ok=True)
for distribution in metadata.distributions():
 name=distribution.metadata.get('Name','unknown')
 for f in distribution.files or []:
  path=str(f).replace('\\','/');base=Path(path).name.lower()
  if ('license' in base or base.startswith('copying') or base.startswith('notice')) and '..' not in Path(path).parts:
   src=Path(distribution.locate_file(f))
   if src.is_file() and src.stat().st_size<4*1024*1024:
    target=licenses/name/Path(path);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
runtime=Path(sys.base_prefix)/'LICENSE.txt'
if runtime.exists():shutil.copyfile(runtime,licenses/'Python-LICENSE.txt')
for src in (root/'licenses').glob('*'):
 if src.is_file():shutil.copyfile(src,licenses/src.name)
for name in ['README.md','使用说明.md','THIRD_PARTY_NOTICES.md','requirements-lock.txt','VALIDATION.md','SECURITY_FIXES.md']:
 shutil.copyfile(root/name,dist/name)
source=dist/'source';source.mkdir(exist_ok=True)
for name in ['scorestudio','tools','tests','licenses']:
 shutil.copytree(root/name,source/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for name in ['main.py','requirements.txt','requirements-lock.txt','PLAN.md','README.md','THIRD_PARTY_NOTICES.md','SCSBOA-Score-Studio.spec']:
 shutil.copyfile(root/name,source/name)
out=release_root/'SCSBOA-Score-Studio-Windows.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for path in dist.rglob('*'):
  if path.is_file():z.write(path,path.relative_to(dist.parent))
print(out,round(out.stat().st_size/1024/1024,1),'MB')
