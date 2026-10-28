import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from scorestudio.model import blank_record,warnings,validate
from scorestudio.storage import Library

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='tmp');self.root=Path(self.temp.name)
        self.lib=Library(self.root/'one');self.other=None
        self.source=self.root/'original.png';self.source.write_bytes(b'original-test-bytes')
        self.record=blank_record();self.record.update(date='2026-10-24',event='Loara FT',division='5AA',school='Arroyo',original_school='Arroyo')
        self.record['scores']={'total':78.2,'subtotal':78.2,'music.total':31.8,'ge.total':30.6,'visual.total':15.8,'penalties.total':0}
        self.record['sources']=[self.lib.stage_source(self.source)]
    def tearDown(self):
        self.lib.db.close()
        if self.other:self.other.db.close()
        self.temp.cleanup()
    def save(self,r):return self.lib.commit([r],'test',lambda *args:None)
    def test_confirmation_boundary_and_persistence(self):
        self.assertEqual(self.lib.records(),[]);self.lib.preview([self.record]);self.assertEqual(self.lib.records(),[])
        self.save(self.record);self.lib.db.close();self.lib=Library(self.root/'one');self.assertEqual(self.lib.records()[0]['scores']['total'],78.2)
    def test_duplicate_and_complement_undo(self):
        self.save(self.record);self.save(self.record);self.assertEqual(len(self.lib.records()),1);self.assertEqual(len(self.lib.history()),1)
        extra=copy.deepcopy(self.record);extra['scores']['auxiliary.total']=82.5;self.save(extra)
        self.assertEqual(self.lib.records()[0]['scores']['auxiliary.total'],82.5)
        self.lib.undo();self.assertNotIn('auxiliary.total',self.lib.records()[0]['scores'])
        self.lib.undo();self.assertEqual(self.lib.records(),[])
    def test_conflict_cancel_is_atomic(self):
        self.save(self.record);changed=copy.deepcopy(self.record);changed['scores']['total']=80
        new=copy.deepcopy(self.record);new['school']='Other'
        self.assertFalse(self.lib.commit([new,changed],'cancel',lambda *a:None));self.assertEqual(len(self.lib.records()),1)
        self.lib.commit([changed],'resolved',lambda a,b,c:{('scores','total'):'incoming'})
        self.assertEqual(self.lib.records()[0]['scores']['total'],80)
        self.lib.undo();self.assertEqual(self.lib.records()[0]['scores']['total'],78.2)
    def test_package_roundtrip_includes_originals(self):
        self.save(self.record);path=self.root/'test.scsboa';self.lib.export_package(path)
        self.other=Library(self.root/'two');rows=self.other.read_package(path)
        self.assertEqual(self.other.records(),[])
        self.other.commit(rows,'import',lambda *a:None)
        self.assertEqual(self.lib.records(),self.other.records())
        self.assertEqual(self.other.asset_path(rows[0]['sources'][0]).read_bytes(),self.source.read_bytes())
    def test_malicious_package_paths_and_versions_rejected(self):
        r=copy.deepcopy(self.record);r['sources'][0]['asset']='../../outside.png'
        p=self.root/'bad.scsboa'
        with zipfile.ZipFile(p,'w') as z:z.writestr('manifest.json',json.dumps({'format':'scsboa-score-studio','version':1,'records':[r]}))
        with self.assertRaises(ValueError):self.lib.read_package(p)
        with zipfile.ZipFile(p,'w') as z:z.writestr('manifest.json',json.dumps({'format':'scsboa-score-studio','version':99,'records':[]}))
        with self.assertRaises(ValueError):self.lib.read_package(p)
    def test_corrupted_original_rejected(self):
        p=self.root/'bad.scsboa';src=self.record['sources'][0]
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('manifest.json',json.dumps({'format':'scsboa-score-studio','version':1,'records':[self.record]}))
            z.writestr('assets/'+src['asset'],b'altered')
        with self.assertRaises(ValueError):self.lib.read_package(p)
    def test_missing_and_invalid_numbers(self):
        self.assertTrue(any('Auxiliary' in x for x in warnings(self.record)))
        self.record['scores']['total']=float('nan')
        with self.assertRaises(ValueError):validate(self.record)
    def test_division_identity_preserved(self):
        self.save(self.record);r=copy.deepcopy(self.record);r['division']='5A';self.save(r)
        self.assertEqual(len(self.lib.records()),2)

if __name__=='__main__':unittest.main()
