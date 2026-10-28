"""Offline extraction for the SCSBOA recap grid. No HTTP clients or downloads."""
import copy
import re
import math
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps
from .model import COLUMNS,blank_record

MAX_PIXELS=40_000_000
MAX_SIDE=20_000
MAX_BATCH_PIXELS=400_000_000
MAX_SOURCE_BYTES=100*1024*1024
IMAGE_FORMATS={'.png':'PNG','.jpg':'JPEG','.jpeg':'JPEG','.webp':'WEBP','.bmp':'BMP',
               '.tif':'TIFF','.tiff':'TIFF','.heic':'HEIF','.heif':'HEIF'}

def checked_pixels(width,height,scale=1):
    if not all(math.isfinite(v) and v>0 for v in (width,height,scale)):
        raise ValueError('Invalid image dimensions or render scale.')
    w,h=math.ceil(width*scale),math.ceil(height*scale)
    if w>MAX_SIDE or h>MAX_SIDE or w*h>MAX_PIXELS:
        raise ValueError('Image or rendered PDF page exceeds 40 megapixels or a 20,000-pixel side. Resize or re-export before import.')
    return w*h

def open_supported_image(path):
    expected=IMAGE_FORMATS.get(Path(path).suffix.lower())
    if expected is None:raise ValueError('Unsupported image format.')
    if expected=='HEIF':
        from pillow_heif import register_heif_opener
        register_heif_opener()
    im=Image.open(path,formats=[expected])
    try:
        if im.format!=expected:raise ValueError('Image content does not match its file extension.')
        checked_pixels(*im.size)
    except Exception:
        im.close();raise
    return im

def inspect_source(path,scale=3):
    path=Path(path)
    if path.stat().st_size>MAX_SOURCE_BYTES:raise ValueError('Source exceeds 100 MB.')
    if path.suffix.lower()=='.pdf':
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(str(path)) as doc:
            if not 1<=len(doc)<=100:raise ValueError('PDF must contain 1 to 100 pages. Split it before import.')
            pixels=[]
            for index in range(len(doc)):
                page=doc[index]
                try:pixels.append(checked_pixels(*page.get_size(),scale))
                finally:page.close()
            return pixels
    with open_supported_image(path) as im:return [checked_pixels(*im.size)]

def load_image(path,page=1,scale=3):
    path=Path(path)
    if path.stat().st_size>MAX_SOURCE_BYTES:raise ValueError('Source exceeds 100 MB.')
    if type(page) is not int or not 1<=page<=100:raise ValueError('Invalid page number.')
    if path.suffix.lower()=='.pdf':
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(str(path)) as doc:
            if len(doc)>100:raise ValueError('PDF exceeds 100 pages. Split it before import.')
            if page>len(doc):raise ValueError('PDF page is out of range.')
            p=doc[page-1]
            try:
                checked_pixels(*p.get_size(),scale)
                bitmap=p.render(scale=scale)
                try:return bitmap.to_pil().convert('RGB')
                finally:bitmap.close()
            finally:p.close()
    with open_supported_image(path) as im:
        return ImageOps.exif_transpose(im).convert('RGB')


def runs(indices):
    groups=[]
    for i in indices:
        if not groups or i>groups[-1][-1]+2: groups.append([int(i)])
        else: groups[-1].append(int(i))
    return [int(sum(g)/len(g)) for g in groups]

def grids(image):
    import cv2
    gray=cv2.cvtColor(np.asarray(image),cv2.COLOR_RGB2GRAY)
    mask=cv2.threshold(gray,95,255,cv2.THRESH_BINARY_INV)[1]
    hmask=cv2.threshold(gray,175,255,cv2.THRESH_BINARY_INV)[1]
    horizontal=cv2.morphologyEx(hmask,cv2.MORPH_OPEN,np.ones((1,max(80,image.width//3)),np.uint8))
    ys=runs(np.where(np.sum(horizontal>0,axis=1)>image.width*.4)[0])
    blocks=[]
    for y in ys:
        if not blocks or y-blocks[-1][-1]>max(80,image.height*.055): blocks.append([y])
        else: blocks[-1].append(y)
    result=[]
    for ys in blocks:
        if len(ys)<2: continue
        # Header horizontal lines do not extend over the school column. Use the leftmost row lines.
        starts=[int(np.where(horizontal[y]>0)[0][0]) for y in ys]
        left=min(starts)
        data_ys=[y for y,start in zip(ys,starts) if start<=left+5]
        if len(data_ys)<2:
            # Retain a partial table's header to carry its division across PDF pages.
            if data_ys:result.append({'xs':[],'ys':data_ys,'top':data_ys[0],'bottom':data_ys[-1],'partial':True})
            continue
        top,bottom=data_ys[0],data_ys[-1]
        vertical=cv2.morphologyEx(mask[top:bottom+1],cv2.MORPH_OPEN,
                     np.ones((max(8,int((bottom-top)*.7)),1),np.uint8))
        xs=runs(np.where(np.sum(vertical>0,axis=0)>(bottom-top)*.7)[0])
        xs=[x for x in xs if x>left+5]
        if len(xs)<18: continue
        typical=float(np.median(np.diff(data_ys)))
        tail=mask[bottom+1:min(image.height,bottom+int(typical*1.4)),xs]
        continuation=np.where(np.sum(tail>0,axis=1)>len(xs)*.7)[0]
        if len(continuation):
            end=bottom+1+int(continuation[-1])
            if typical*.9<=end-bottom<=typical*1.15:data_ys.append(end);bottom=end
        # Only complete cells are read. A cut-off right edge is deliberately excluded.
        result.append({'xs':[left]+xs,'ys':data_ys,'top':top,'bottom':bottom})
    return result

class Recognizer:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,det_limit_side_len=1600,det_limit_type='max')

    def full_text(self,image):
        output,_=self.engine(np.asarray(image),use_cls=False)
        return output or []

    def recognize_cells(self,images):
        if not images: return []
        import cv2
        prepared=[]
        for im in images:
            arr=np.asarray(im).copy()
            # Rasterized PDF rules can extend 1–2 pixels inside a crop. Remove only
            # border-touching, near-full-height/width strokes, not interior glyphs.
            for _ in range(3):
                if min(arr.shape[:2])<=3:break
                gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
                if np.mean(gray[:,0]<135)>.85:arr=arr[:,1:]
                if np.mean(gray[:,-1]<135)>.85:arr=arr[:,:-1]
                gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
                if np.mean(gray[0,:]<135)>.85:arr=arr[1:,:]
                if np.mean(gray[-1,:]<135)>.85:arr=arr[:-1,:]
            gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY)
            ink=gray<135
            yy,xx=np.where(ink)
            if len(xx):
                arr=arr[yy.min():yy.max()+1,xx.min():xx.max()+1]
            scale=max(1,42/max(1,arr.shape[0]))
            arr=cv2.resize(arr,None,fx=scale,fy=scale,interpolation=cv2.INTER_CUBIC)
            prepared.append(cv2.copyMakeBorder(arr,5,5,5,5,cv2.BORDER_CONSTANT,value=(255,255,255)))
        output,_=self.engine.text_rec(prepared)
        return output

    def parse(self,image,source,progress=lambda s:None,previous=None,text_words=None,cancelled=lambda:False):
        progress('Reading page headings and table structure…')
        # Prefer real PDF text, where available, for heading metadata.
        tables=grids(image)
        words=text_words or []
        if not text_words:
            for table in tables:
                start=max(0,table['top']-max(260,int(image.height*.16)))
                crop=image.crop((0,start,image.width,table['top']))
                for box,text,confidence in self.full_text(crop):
                    words.append(([[x,y+start] for x,y in box],text,confidence))
        positioned=[]
        for box,text,confidence in words:
            positioned.append((sum(p[1] for p in box)/4,text,confidence))
        positioned.sort(key=lambda w:w[0])
        records=[]; notices=[]
        context=previous or {}
        for table in tables:
            if cancelled():break
            top=table['top']; xs=table['xs']; ys=table['ys']
            above=[(y,t) for y,t,c in positioned if y<top]
            event=context.get('event',''); date=context.get('date',''); division=context.get('division','')
            for y,t in above:
                match=re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(20\d{2})',t,re.I)
                if match:
                    date=datetime.strptime(' '.join(match.groups()),'%B %d %Y').date().isoformat()
                    headings=[s for yy,s in above if yy<y and (re.search(r'\bFT\b|Tournament|Invitational|Championship',s,re.I))]
                    if headings: event=headings[-1]
                if re.fullmatch(r'(?:[1-6]\s*A{1,2}(?:\s+(?:RED|BLACK))?|Exhibition)',t.strip(),re.I):
                    division=re.sub(r'(?<=\d)\s+(?=A)','',t.strip()).upper()
            context={'event':event,'date':date,'division':division,'supported':context.get('supported',False)}
            # Do not interpret a different scoring layout using fixed column offsets.
            header=' '.join(t for y,t in above if y>top-image.height*.19).lower()
            supported=('music' in header and ('visual' in header or 'vis' in header))
            if table.get('partial'):
                notices.append(f'{division}: partial table at page edge; check the split row against another image.')
                context['supported']=supported
                continue
            if top<image.height*.1 and context.get('supported'):
                supported=True
                notices.append(f'{division}: continued table; confirm inherited event, division and column mapping.')
            if not supported:
                notices.append('A table header was incomplete. Check column mapping; continuation rows may need manual entry.')
                continue
            context['supported']=True
            count=min(len(COLUMNS),len(xs)-2)
            if count<29: notices.append(f'{division}: right-hand columns are cropped or incomplete; unavailable cells are Missing.')
            for row_index,(y1,y2) in enumerate(zip(ys,ys[1:])):
                if cancelled():break
                if y2-y1<10: continue
                progress(f'Reading {division or "table"} · row {row_index+1}…')
                mid=(y1+y2)//2
                school_image=image.crop((xs[0]+1,y1+2,xs[1]-1,mid+1))
                crops=[school_image]
                for j in range(count):
                    a,b=xs[j+1],xs[j+2]
                    crops.append(image.crop((a+2,y1+2,b-2,mid+1)))
                    crops.append(image.crop((a+2,mid,b-2,y2-1)))
                out=self.recognize_cells(crops)
                school=str(out[0][0]).strip() if out else ''
                if not school: continue
                r=blank_record(); r.update(context); r['school']=school; r['original_school']=school
                if date: r['season']=date[:4]
                r['sources']=[copy.deepcopy(source)]; low=[]
                for judge,start_col,end_col in [('music.j1',1,4),('music.j2',4,7),('ge.j1',8,11),('ge.j2',11,14),('visual',15,18),('penalties',19,20),('auxiliary',22,25),('percussion',26,29)]:
                    if end_col>=len(xs):continue
                    candidates=[]
                    for box,text,confidence in words:
                        x=sum(p[0] for p in box)/4;y=sum(p[1] for p in box)/4
                        if xs[start_col]<=x<=xs[end_col] and top-max(80,image.height*.035)<y<top:
                            if re.match(r'^[A-Z]\.\s*\w',text.strip()):candidates.append((y,text.strip()))
                    if candidates:r['judges'][judge]=sorted(candidates)[-1][1]
                for j in range(count):
                    key=COLUMNS[j][0]
                    for offset,category in [(1,'scores'),(2,'ranks')]:
                        raw,confidence=out[2*j+offset]
                        # Do not silently repair decimal points or substitute letters for digits.
                        token=str(raw).strip().replace(' ','')
                        if re.fullmatch(r'-?\d+(?:\.\d+)?',token):
                            value=float(token)
                            if category=='ranks' and (value<1 or int(value)!=value):
                                low.append(key+' rank'); continue
                            r[category][key]=value
                            if confidence<.9: low.append(key)
                        elif token: low.append(key+' '+category)
                # Judge labels remain editable; preserve OCR header as audit context.
                r['notes']='Imported using SCSBOA field grid. Verify all scores and ranks.'
                if count<29: r['notes']+=' Right edge cropped: some captions are missing.'
                if low: r['notes']+=' Check OCR: '+', '.join(sorted(set(low)))
                r['header_text']=' | '.join(t for y,t in above if y>top-image.height*.16)
                records.append(r)
        if not records:
            notices.append('No complete supported grid found. Add records manually using the original, or import a clearer screenshot.')
        return records,notices,context

def import_files(paths,library,progress,cancelled=lambda:False):
    if len(paths)>100:raise ValueError('Import at most 100 files per batch.')
    if sum(Path(path).stat().st_size for path in paths)>512*1024*1024:
        raise ValueError('Batch exceeds 512 MB. Import fewer files at a time.')
    prepared=[];pixel_budget=0
    for path in paths:
        if cancelled():return [],[],[]
        progress('Checking file limits: '+Path(path).name)
        source=library.stage_source(path);staged=library.asset_path(source)
        pixels=inspect_source(staged)
        pixel_budget+=sum(pixels)
        if pixel_budget>MAX_BATCH_PIXELS:raise ValueError('Batch exceeds 400 megapixels of decoded pages. Import fewer files at a time.')
        prepared.append((staged,source,len(pixels)))
    recognizer=Recognizer(); all_rows=[]; notices=[]; sources=[]
    for path,source,pages in prepared:
        if cancelled(): break
        progress('Opening '+source['name'])
        sources.append(source);text_pdf=None
        previous={}
        try:
            if Path(path).suffix.lower()=='.pdf':
                import pdfplumber
                text_pdf=pdfplumber.open(path)
                if len(text_pdf.pages)!=pages:raise ValueError('PDF page count is inconsistent. Re-export the PDF before import.')
            for page in range(1,pages+1):
                if cancelled(): break
                src=copy.deepcopy(source); src['page']=page
                image=load_image(path,page)
                words=None
                if text_pdf and len(text_pdf.pages[page-1].chars)>20:
                    words=[]
                    for w in text_pdf.pages[page-1].extract_words():
                        x1,y1,x2,y2=[w[k]*3 for k in ['x0','top','x1','bottom']]
                        words.append(([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],w['text'],1))
                    # Extracted individual words are also retained, but OCR joins headings reliably.
                    words=words+recognizer.full_text(image)
                rows,issues,previous=recognizer.parse(image,src,progress,previous,words,cancelled)
                all_rows.extend(rows)
                notices.extend(f"{source['name']} · p{page}: {s}" for s in issues)
            if pages>1:
                notices.append(f"{source['name']}: check every page and division for split or clipped rows. Incomplete rows at a page break may require Add record or a complete screenshot; recognition is not a completeness guarantee.")
        finally:
            if text_pdf: text_pdf.close()
    return all_rows,notices,sources
