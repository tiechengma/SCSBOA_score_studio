"""Headless Qt integration test, using an isolated temporary library only."""
import copy,json,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication,QMessageBox,QTabWidget,QTableWidget,QDialog,QComboBox
from PySide6.QtGui import QFontDatabase
from PySide6.QtCore import Qt,QTimer
from PySide6.QtTest import QTest
from scorestudio.app import MainWindow
from scorestudio.widgets import STYLE
from scorestudio.storage import Library
from scorestudio.model import DEFAULT_SCHOOL,school_key,COLUMNS,MAIN

app=QApplication([])
for font in ['segoeui.ttf','segoeuib.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
app.setStyle('Fusion');app.setStyleSheet(STYLE)
with tempfile.TemporaryDirectory(dir='tmp') as temp:
 w=MainWindow(temp);w.show();app.processEvents()
 assert w.stack.currentWidget() is w.school_page
 assert [b.text().replace('&&','&') for b in w.nav]==['Schools','Events','Season overview','Import & review','Data Management']
 assert w.school_page.selector.currentText()==DEFAULT_SCHOOL
 rows=json.loads(Path('tmp/final-sample-records.json').read_text(encoding='utf8'))
 sources={}
 for row in rows:
  filename=row['sources'][0]['name']
  if filename not in sources:sources[filename]=w.library.stage_source(Path(sys.argv[1])/filename)
  row['sources']=[sources[filename]]
 w.review.load(rows,[],list(sources.values()));w.navigate(3);app.processEvents()
 assert len(w.library.records())==0
 assert w.review.current==0
 w.review.findChild(QTabWidget).setCurrentIndex(1);app.processEvents()
 w.grab().save('tmp/verified-review.png')
 # Edits survive switching rows without entering the library prematurely.
 w.review.fields['school'].setText('Edited name');w.review.pending.selectRow(1);app.processEvents()
 assert w.review.rows[0]['school']=='Edited name'
 w.review.pending.selectRow(0);w.review.fields['school'].setText(rows[0]['school'])
 original=QMessageBox.question;QMessageBox.question=lambda *args,**kwargs:QMessageBox.Yes
 try:w.review.save_batch()
 finally:QMessageBox.question=original
 assert len(w.library.records())==10
 assert len(w.review.rows)==0
 w.navigate(1);event=w.event_page;event.selector.setCurrentIndex(0);app.processEvents()
 assert len(set(r['division'] for r in event.visible))==1
 assert len(event.visible)==7
 assert max(v for l,v in event.chart.points)==71.9
 assert event.chart.first_indices=={0}
 assert event.honors.isHidden() and len(event.cards)==2
 w.grab().save('tmp/verified-events.png')
 event.selector.setCurrentIndex(1);app.processEvents();assert len(event.visible)==3
 assert max(v for l,v in event.chart.points)==78.2
 w.navigate(0);app.processEvents();w.grab().save('tmp/verified-school.png')
 assert w.school_page.selector.currentText()==DEFAULT_SCHOOL
 assert len(w.school_page.visible)==1
 assert len(w.school_page.cards)==2
 assert not w.school_page.honors.isHidden()
 # Exercise real chart hit targets and modal detail content.
 failures=[]
 def choose_whole_record():
  dialog=app.activeModalWidget()
  try:
   choice=dialog.findChild(QComboBox)
   assert choice.itemText(1)=='Keep entire saved record'
   assert choice.itemText(2)=='Replace entire record'
   choice.setCurrentIndex(2);dialog.accept_choices()
  except Exception as e:
   failures.append(e);dialog.reject()
 QTimer.singleShot(100,choose_whole_record)
 choice=w.resolve(rows[0],rows[0],[('record','scheme','old-system','new-system')])
 assert choice=={('record','scheme'):'incoming'} and not failures
 def inspect_detail():
  dialog=app.activeModalWidget()
  try:
   assert isinstance(dialog,QDialog)
   scores=dialog.findChild(QTableWidget,'detailScores');assert scores is not None
   for i,(key,title) in enumerate(COLUMNS):
    assert scores.item(i,0).font().bold()==(key in MAIN),key
    assert scores.item(i,1).font().bold()==(key in MAIN),key
   assert scores.item(20,1).text()=='78.2'
   tabs=dialog.findChild(QTabWidget);assert [tabs.tabText(i) for i in range(tabs.count())]==['Scores && ranks','Original','Source awards']
   dialog.grab().save('tmp/verified-click-detail.png')
  except Exception as e:failures.append(e)
  finally:
   if dialog:dialog.reject()
 school=w.school_page;app.processEvents()
 QTimer.singleShot(100,inspect_detail)
 QTest.mouseClick(school.chart,Qt.LeftButton,pos=school.chart.hit_regions[0][1].center().toPoint())
 assert not failures,failures
 w.navigate(1);app.processEvents()
 QTimer.singleShot(100,inspect_detail)
 QTest.mouseClick(event.chart,Qt.LeftButton,pos=event.chart.hit_regions[0][1].center().toPoint())
 assert not failures,failures
 w.navigate(2);app.processEvents();season=w.season_page
 assert season.chart.points[0][1]==10
 def inspect_rankings():
  dialog=app.activeModalWidget()
  try:
   grid=dialog.findChild(QTableWidget,'eventRankings');assert grid.rowCount()==10
   assert [grid.item(i,0).text() for i in range(10)]==['4A']*7+['5AA']*3
   assert grid.item(0,2).text()=='71.9' and grid.item(7,2).text()=='78.2'
   dialog.grab().save('tmp/verified-rankings.png')
   QTimer.singleShot(100,inspect_detail)
   QTest.mouseClick(grid.viewport(),Qt.LeftButton,pos=grid.visualItemRect(grid.item(7,1)).center())
  except Exception as e:failures.append(e)
  finally:
   if dialog:dialog.reject()
 QTimer.singleShot(100,inspect_rankings)
 QTest.mouseClick(season.chart,Qt.LeftButton,pos=season.chart.hit_regions[0][1].center().toPoint())
 assert not failures,failures
 w.navigate(0);app.processEvents()
 def inspect_expanded():
  dialog=app.activeModalWidget()
  try:
   from scorestudio.widgets import Chart
   chart=dialog.findChild(Chart);assert chart.height()>=450
   dialog.grab().save('tmp/verified-expanded.png')
   QTimer.singleShot(100,inspect_detail)
   QTest.mouseClick(chart,Qt.LeftButton,pos=chart.hit_regions[0][1].center().toPoint())
  except Exception as e:failures.append(e)
  finally:
   if dialog:dialog.reject()
 QTimer.singleShot(100,inspect_expanded);school.expand_chart()
 assert not failures,failures
 # Drag movement must not activate a record; missing points have no hit region.
 from scorestudio.widgets import Chart
 probe=Chart();probe.resize(600,400);probe.set_data([('Missing',None),('Zero',0)],'bar','Test');probe.show();app.processEvents()
 assert [i for i,r in probe.hit_regions]==[1]
 emitted=[];probe.activated.connect(emitted.append);center=probe.hit_regions[0][1].center().toPoint()
 QTest.mousePress(probe,Qt.LeftButton,pos=center);QTest.mouseRelease(probe,Qt.LeftButton,pos=center+type(center)(20,0))
 assert emitted==[];probe.close()
 # One filter selects an exact season/scoring pair, never a cross-product.
 original_records=w.library.records
 sample=copy.deepcopy(original_records()[0]);sample['season']='2027';sample['scheme']='custom-2027'
 alternate=copy.deepcopy(sample);alternate['scheme']='alternate-2027'
 w.library.records=lambda:original_records()+[sample,alternate]
 w.school_page.refresh()
 combined=w.school_page.season_filter
 combined.setCurrentIndex(combined.findData(('2027','custom-2027')))
 assert w.school_page.filtered()==[sample]
 w.school_page.refresh();assert tuple(combined.currentData())==('2027','custom-2027')
 w.library.records=original_records;w.school_page.refresh();w.school_page.select_default()
 assert tuple(combined.currentData())==('2026','scsboa-field-2026')
 w.resize(1100,740);app.processEvents();w.grab().save('tmp/verified-compact.png')
 assert w.width()==1100
 w.resize(1480,960);app.processEvents()
 w.navigate(4);app.processEvents();w.grab().save('tmp/verified-management.png')
 w.management.default_school.setCurrentText('Wilson HS');w.management.save_default()
 assert w.library.default_school()=='Wilson HS'
 assert w.school_page.selector.currentText()=='Wilson HS'
 w.review.add_record();assert w.review.rows[0]['school']=='Wilson HS';w.review.rows=[];w.review.current=-1
 # Source awards are editable without changing score values.
 stored=w.library.records()[0]
 w.library.update_awards(stored,{'Fixture award':'Synthetic test source only'})
 assert w.library.records()[0]['awards']=={'Fixture award':'Synthetic test source only'}
 w.library.undo();assert w.library.default_school()=='Wilson HS'
 package=Path(temp)/'roundtrip.scsboa';w.library.export_package(package)
 other=Library(Path(temp)/'other');incoming=other.read_package(package)
 other.commit(incoming,'test',lambda *a:None)
 assert len(other.records())==10
 assert all(other.asset_path(src).exists() for r in other.records() for src in r['sources'])
 other.db.close();w.library.undo();w.refresh_all();assert len(w.library.records())==0
 w.library.db.close()
print('PASS: navigation, default/alias, preferences, manual entry, awards, gold firsts, draft boundary, grouping, package roundtrip and undo')
