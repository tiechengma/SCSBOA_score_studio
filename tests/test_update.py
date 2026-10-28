import copy,json,tempfile,unittest,zipfile
from pathlib import Path
from scorestudio.model import DEFAULT_SCHOOL,SCHEMA,blank_record,leaders,school_key,validate
from scorestudio.storage import Library

class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='tmp');self.root=Path(self.temp.name);self.lib=Library(self.root/'library')
        self.row=blank_record();self.row.update(school='Arroyo Knights Band & Colorguard',original_school='Arroyo Knights Band & Colorguard',event='Loara FT',date='2026-10-24',division='5AA')
        self.row['scores']={'total':78.2,'music.total':31.8};self.row['ranks']={'total':1,'music.total':1}
    def tearDown(self):self.lib.db.close();self.temp.cleanup()
    def save(self,r):return self.lib.commit([r],'reviewed',lambda *args:None)
    def test_default_persists_and_is_not_exported(self):
        self.assertEqual(self.lib.default_school(),DEFAULT_SCHOOL)
        self.lib.set_default_school('Wilson HS');self.lib.db.close();self.lib=Library(self.root/'library')
        self.assertEqual(self.lib.default_school(),'Wilson HS')
        p=self.root/'share.scsboa';self.lib.export_package(p)
        with zipfile.ZipFile(p) as z:self.assertNotIn('default_school',z.read('manifest.json').decode())
    def test_alias_matches_without_changing_source_name(self):
        self.save(self.row);incoming=copy.deepcopy(self.row);incoming['school']=DEFAULT_SCHOOL
        self.assertEqual(self.lib.preview([incoming])['duplicate'],1)
        self.save(incoming);self.assertEqual(len(self.lib.records()),1)
        self.assertEqual(self.lib.records()[0]['school'],'Arroyo Knights Band & Colorguard')
        self.assertEqual(school_key(self.row['school']),school_key(DEFAULT_SCHOOL))
    def test_awards_edit_and_undo_preserve_preference_and_scores(self):
        self.save(self.row);self.lib.set_default_school('Wilson HS')
        self.lib.update_awards(self.row,{'Fixture award':'Synthetic source, page 1'})
        saved=self.lib.records()[0];self.assertEqual(saved['scores'],self.row['scores'])
        self.assertEqual(saved['awards'],{'Fixture award':'Synthetic source, page 1'})
        self.lib.undo();self.assertEqual(self.lib.records()[0]['awards'],{})
        self.assertEqual(self.lib.default_school(),'Wilson HS')
    def test_awards_roundtrip_and_conflicts(self):
        self.row['awards']={'Fixture award':'Page 1'};self.save(self.row)
        p=self.root/'new.scsboa';self.lib.export_package(p)
        with zipfile.ZipFile(p) as z:self.assertEqual(json.loads(z.read('manifest.json'))['version'],2)
        self.assertEqual(self.lib.read_package(p)[0]['awards'],self.row['awards'])
        changed=copy.deepcopy(self.row);changed['awards']['Fixture award']='Page 2'
        self.assertEqual(self.lib.preview([changed])['conflict'],1)
        self.assertFalse(self.save(changed))
        self.lib.commit([changed],'resolved',lambda *args:{('awards','Fixture award'):'incoming'})
        self.assertEqual(self.lib.records()[0]['awards']['Fixture award'],'Page 2')
    def test_version_one_package_and_local_records_remain_readable(self):
        old=copy.deepcopy(self.row);old.pop('awards');self.save(old)
        p=self.root/'old.scsboa'
        with zipfile.ZipFile(p,'w') as z:z.writestr('manifest.json',json.dumps({'format':'scsboa-score-studio','version':1,'records':[old]}))
        rows=self.lib.read_package(p);self.assertNotIn('awards',rows[0]);self.assertEqual(self.lib.preview(rows)['duplicate'],1)
    def test_tied_source_firsts_are_all_highlighted(self):
        other=copy.deepcopy(self.row);other['school']='Other HS'
        kind,rows=leaders([self.row,other],'total');self.assertEqual(kind,'source');self.assertEqual(len(rows),2)
    def test_partial_group_never_invents_official_first(self):
        self.row['ranks']['total']=2
        kind,rows=leaders([self.row],'total');self.assertEqual(kind,'imported');self.assertEqual(len(rows),1)
        self.row['ranks'].clear();self.assertEqual(leaders([self.row],'total')[0],'imported')
        self.assertEqual(leaders([self.row],'visual.total'),('missing',[]))
    def test_awards_require_source_notes(self):
        self.row['awards']={'Sweepstakes':''}
        with self.assertRaises(ValueError):validate(self.row)

if __name__=='__main__':unittest.main()
