import copy,hashlib,io,json,struct,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import pypdfium2 as pdfium
from scorestudio.model import blank_record,validate
from scorestudio.storage import Library
from scorestudio.recognition import load_image,import_files


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='tmp');self.root=Path(self.temp.name)
        self.lib=Library(self.root/'library')
        self.row=blank_record();self.row.update(date='2026-10-24',school='Test school',event='Test event',division='4A')
        self.row['scores']={'music.total':31.8}

    def tearDown(self):
        self.lib.db.close();self.temp.cleanup()

    def package(self,rows,asset=None):
        path=self.root/'input.scsboa'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('manifest.json',json.dumps({'format':'scsboa-score-studio','version':2,'records':rows}))
            if asset:z.writestr('assets/'+asset[0],asset[1])
        return path

    def test_strict_package_numbers(self):
        for bad in ('78.2','',True,False,[],{},float('nan'),float('inf')):
            for category in ('scores','ranks'):
                with self.subTest(value=bad,category=category):
                    row=copy.deepcopy(self.row);row[category]['total']=bad
                    with self.assertRaises(ValueError):self.lib.read_package(self.package([row]))
        self.assertEqual(self.lib.records(),[])

    def test_bad_record_and_manifest_are_rejected(self):
        for row in (None,[],False,'record'):
            with self.assertRaises(ValueError):self.lib.read_package(self.package([row]))
        path=self.root/'bad.scsboa'
        with zipfile.ZipFile(path,'w') as z:z.writestr('manifest.json','[]')
        with self.assertRaises(ValueError):self.lib.read_package(path)

    def test_cross_scheme_is_whole_record_choice(self):
        self.lib.commit([self.row],'initial',lambda *a:None)
        incoming=copy.deepcopy(self.row);incoming['scheme']='different-scale';incoming['scores']={'ge.total':99};incoming['awards']={'New award':'New source'}
        self.assertEqual(self.lib.preview([incoming])['conflict'],1)
        for decision in ('saved','incoming'):
            self.lib.commit([incoming],'resolved',lambda a,b,c:{('record','scheme'):decision})
            self.assertEqual(self.lib.records()[0],self.row if decision=='saved' else incoming)
        self.lib.undo();self.assertEqual(self.lib.records()[0],self.row)
        self.assertFalse(self.lib.commit([incoming],'cancelled',lambda *a:None))
        self.assertEqual(self.lib.records()[0],self.row)

    def test_casefold_award_conflicts(self):
        self.row['awards']={'Best Music':'Source A'};self.lib.commit([self.row],'first',lambda *a:None)
        incoming=copy.deepcopy(self.row);incoming['awards']={'best music':'Source B'}
        self.assertEqual(self.lib.preview([incoming])['conflict'],1)
        self.lib.commit([incoming],'resolve',lambda a,b,c:{('awards','Best Music'):'incoming'})
        self.assertEqual(self.lib.records()[0]['awards'],{'Best Music':'Source B'});validate(self.lib.records()[0])
        package=self.root/'share.scsboa';self.lib.export_package(package)
        self.assertEqual(self.lib.read_package(package),self.lib.records())

    def test_final_award_limit_rolls_back_batch(self):
        self.row['awards']={str(i):'Source' for i in range(100)};self.lib.commit([self.row],'first',lambda *a:None)
        incoming=copy.deepcopy(self.row);incoming['awards']={'Extra':'Source'}
        new=copy.deepcopy(self.row);new['school']='New school'
        with self.assertRaises(ValueError):self.lib.commit([new,incoming],'bad batch',lambda *a:None)
        self.assertEqual(self.lib.records(),[self.row]);self.assertEqual(len(self.lib.history()),1)

    def test_disguised_psd_and_mismatched_extension_rejected(self):
        path=self.root/'disguised.png'
        path.write_bytes(b'8BPS'+struct.pack('>H',1)+b'\0'*6+struct.pack('>HIIHH',3,1,1,8,3)+b'\0'*12+struct.pack('>H',0)+b'\xff\0\0')
        with self.assertRaises((ValueError,OSError)):load_image(path)
        Image.new('RGB',(2,2)).save(path,format='JPEG')
        with self.assertRaises((ValueError,OSError)):load_image(path)

    def test_image_limit_is_before_pixel_decode(self):
        im=Image.new('RGB',(1,1));im._size=(10000,5000)
        with patch('scorestudio.recognition.Image.open',return_value=im),patch('scorestudio.recognition.ImageOps.exif_transpose') as transpose:
            im.format='PNG'
            with self.assertRaises(ValueError):load_image(self.make_png())
            transpose.assert_not_called()

    def make_png(self):
        path=self.root/'small.png';Image.new('RGB',(2,2)).save(path);return path

    def test_pdf_limit_is_before_render(self):
        path=self.root/'large.pdf';doc=pdfium.PdfDocument.new();page=doc.new_page(2500,2000);doc.save(path);page.close();doc.close()
        with patch.object(pdfium.PdfPage,'render') as render:
            with self.assertRaises(ValueError):load_image(path)
            render.assert_not_called()
        with self.assertRaises(ValueError):load_image(path,page=0)

    def test_batch_pixel_budget_before_ocr(self):
        path=self.make_png()
        with patch('scorestudio.recognition.inspect_source',return_value=[40_000_000]),patch('scorestudio.recognition.Recognizer') as recognizer:
            with self.assertRaises(ValueError):import_files([path]*11,self.lib,lambda s:None)
            recognizer.assert_not_called()
        with self.assertRaises(ValueError):import_files([path]*101,self.lib,lambda s:None)

    def test_cached_original_repairs_and_export_checks_hash(self):
        path=self.make_png();raw=path.read_bytes();source=self.lib.stage_source(path);self.row['sources']=[source]
        package=self.package([self.row],(source['asset'],raw));dest=self.lib.asset_path(source)
        dest.write_bytes(b'damaged');self.lib.read_package(package);self.assertEqual(dest.read_bytes(),raw)
        dest.write_bytes(b'damaged again');self.lib.stage_source(path);self.assertEqual(dest.read_bytes(),raw)
        self.lib.commit([self.row],'save',lambda *a:None)
        output=self.root/'existing.scsboa';output.write_bytes(b'existing export')
        dest.write_bytes(b'broken')
        with self.assertRaises(ValueError):self.lib.export_package(output)
        self.assertEqual(output.read_bytes(),b'existing export')
        self.assertEqual(list(self.root.glob('*.tmp')),[])

    def test_failed_atomic_asset_write_preserves_existing(self):
        path=self.make_png();source=self.lib.stage_source(path);dest=self.lib.asset_path(source);dest.write_bytes(b'old cache')
        with patch('scorestudio.storage.os.replace',side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):self.lib.write_asset(dest,io.BytesIO(path.read_bytes()))
        self.assertEqual(dest.read_bytes(),b'old cache');self.assertEqual(list(self.lib.assets.glob('*.tmp')),[])
        with self.assertRaises(ValueError):self.lib.write_asset(dest,io.BytesIO(b'wrong hash'))
        self.assertEqual(dest.read_bytes(),b'old cache')

    def test_all_package_hashes_checked_before_cache_changes(self):
        path=self.make_png();source=self.lib.stage_source(path);dest=self.lib.asset_path(source);dest.write_bytes(b'damaged')
        row=copy.deepcopy(self.row);row['sources']=[source,dict(source,asset='a'*64+'.png')]
        package=self.package([row],(source['asset'],path.read_bytes()))
        with self.assertRaises(ValueError):self.lib.read_package(package)
        self.assertEqual(dest.read_bytes(),b'damaged')


if __name__=='__main__':unittest.main()
