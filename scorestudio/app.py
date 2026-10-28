import copy
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt,QThread,Signal,QTimer,QUrl,QLockFile,QSize
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QVBoxLayout,QHBoxLayout,
 QLabel,QPushButton,QStackedWidget,QTableWidget,QTableWidgetItem,QHeaderView,QLineEdit,QComboBox,
 QFileDialog,QMessageBox,QSplitter,QFormLayout,QPlainTextEdit,QDialog,QDialogButtonBox,QTabWidget,
 QAbstractItemView,QProgressBar,QSpinBox,QScrollArea,QGroupBox,QCompleter)
from .storage import Library
from .model import COLUMNS,LABELS,MAIN,blank_record,number,validate,warnings,normalized,school_name
from .recognition import import_files,load_image
from .widgets import SourceView,Chart,STYLE,nav_icon
from .ui_common import label,button,table,fill_table,fmt,mark_first,AwardEditor
from .explorer import ExplorerPage
from . import __version__

class ImportWorker(QThread):
    progress=Signal(str); done=Signal(object,object,object); failed=Signal(str)
    def __init__(self,paths,library):super().__init__(); self.paths=paths; self.library=library
    def run(self):
        try:
            rows,notices,sources=import_files(self.paths,self.library,self.progress.emit,self.isInterruptionRequested)
            if not self.isInterruptionRequested(): self.done.emit(rows,notices,sources)
        except Exception as e:self.failed.emit(str(e))

class ConflictDialog(QDialog):
    def __init__(self,old,new,conflicts,parent):
        super().__init__(parent); self.setWindowTitle('Resolve conflicting scores'); self.resize(850,430)
        self.conflicts=conflicts; self.choices=[]; layout=QVBoxLayout(self)
        whole_record=any(category=='record' for category,key,a,b in conflicts)
        layout.addWidget(label(f"{new['school']}  ·  {new['event']}  ·  {new['division']}",'heading'))
        note='Scoring systems differ. Keep the entire saved record or replace it entirely with the incoming record; scores and awards will not be mixed. Cancel leaves the batch unsaved.' if whole_record else 'Choose each field explicitly. Cancel leaves the entire batch unsaved.'
        help_text=label(note,'muted');help_text.setWordWrap(True);layout.addWidget(help_text)
        t=table(['Field','Saved value','Incoming value','Use']); t.setRowCount(len(conflicts))
        for i,(category,key,a,b) in enumerate(conflicts):
            for j,text in enumerate([f'{category}: {LABELS.get(key,key)}',str(a),str(b)]):t.setItem(i,j,QTableWidgetItem(text))
            c=QComboBox(); c.addItems(['Choose…','Keep entire saved record','Replace entire record'] if whole_record else ['Choose…','Keep saved','Use incoming']); t.setCellWidget(i,3,c);self.choices.append(c)
        t.resizeColumnsToContents(); layout.addWidget(t)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_choices);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
    def accept_choices(self):
        if any(c.currentIndex()==0 for c in self.choices):
            QMessageBox.warning(self,'Choose every field','Please choose a value for every conflicting field.');return
        self.accept()
    def result_choices(self):
        return {(cat,key):('incoming' if c.currentIndex()==2 else 'saved') for (cat,key,a,b),c in zip(self.conflicts,self.choices)}

class ReviewPage(QWidget):
    saved=Signal()
    def __init__(self,window):
        super().__init__();self.window=window;self.rows=[];self.sources=[];self.current=-1;self.loading=False;self.notices=[]
        layout=QVBoxLayout(self);layout.setContentsMargins(24,20,24,20)
        layout.addWidget(label('IMPORT & REVIEW','eyebrow'));layout.addWidget(label('Make every score count.','heading'))
        layout.addWidget(label('Verify the originals before adding this batch to your season.','muted'))
        toolbar=QHBoxLayout();toolbar.addWidget(button('Import images / PDF',window.choose_files,True))
        toolbar.addWidget(button('Import data package',window.choose_package));toolbar.addWidget(button('Add record',self.add_record))
        toolbar.addWidget(button('Remove selected',self.remove_record));toolbar.addStretch()
        self.save_button=button('Confirm & save batch',self.save_batch,True);self.save_button.setEnabled(False);toolbar.addWidget(self.save_button);layout.addLayout(toolbar)
        self.message=label('No pending batch. Import a recap or a shared .scsboa package.','muted');self.message.setWordWrap(True);layout.addWidget(self.message)
        layout.addWidget(button('View import notes',lambda:QMessageBox.information(self,'Import notes','\n\n'.join(self.notices) or 'No page-level warnings. Verify every record against the original.')))
        self.pending=table(['School','Event','Date','Division','Final','Checks']);self.pending.setMaximumHeight(180)
        self.pending.itemSelectionChanged.connect(self.select_record);layout.addWidget(self.pending)
        splitter=QSplitter();layout.addWidget(splitter,1)
        left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,8,0)
        sourcebar=QHBoxLayout();self.source=QComboBox();self.source.currentIndexChanged.connect(self.show_source)
        sourcebar.addWidget(self.source,1);sourcebar.addWidget(button('Fit',lambda:self.viewer.fit()))
        sourcebar.addWidget(button('Original',self.open_original));ll.addLayout(sourcebar)
        pagebar=QHBoxLayout();pagebar.addWidget(label('PDF page'));self.page=QSpinBox();self.page.setRange(1,100)
        self.page.valueChanged.connect(self.change_page);pagebar.addWidget(self.page);pagebar.addStretch()
        pagebar.addWidget(button('Attach this page',self.attach_page))
        pagebar.addWidget(label('Scroll to zoom · drag to pan','muted'));ll.addLayout(pagebar)
        self.viewer=SourceView();ll.addWidget(self.viewer,1);splitter.addWidget(left)
        right=QWidget();rl=QVBoxLayout(right);rl.setContentsMargins(8,0,0,0);tabs=QTabWidget();rl.addWidget(tabs)
        meta=QWidget();form=QFormLayout(meta);self.fields={}
        for key,title in [('school','School'),('original_school','Original school'),('event','Event'),('date','Date (YYYY-MM-DD)'),('season','Season'),('division','Official division'),('scheme','Scoring scheme')]:
            w=QLineEdit();form.addRow(title,w);self.fields[key]=w
        self.fields['school'].setPlaceholderText('Use a consistent name across imports')
        self.notes=QPlainTextEdit();self.notes.setMaximumHeight(100);form.addRow('Notes',self.notes)
        self.judges={}
        for key,title in [('music.j1','Music judge 1'),('music.j2','Music judge 2'),('ge.j1','GE judge 1'),('ge.j2','GE judge 2'),('visual','Visual judge'),('penalties','Penalty judge'),('auxiliary','Auxiliary judge'),('percussion','Percussion judge')]:
            w=QLineEdit();form.addRow(title,w);self.judges[key]=w
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(meta);tabs.addTab(scroll,'Details && judges')
        self.scores=table(['Caption / printed column','Score','Rank']);self.scores.setRowCount(len(COLUMNS))
        self.scores.setEditTriggers(QAbstractItemView.DoubleClicked|QAbstractItemView.EditKeyPressed|QAbstractItemView.AnyKeyPressed)
        for i,(key,title) in enumerate(COLUMNS):
            item=QTableWidgetItem(title);item.setFlags(item.flags()&~Qt.ItemIsEditable);self.scores.setItem(i,0,item)
            self.scores.setItem(i,1,QTableWidgetItem(''));self.scores.setItem(i,2,QTableWidgetItem(''))
        self.scores.setColumnWidth(0,255);self.scores.setColumnWidth(1,95);tabs.addTab(self.scores,'Scores && ranks')
        self.awards=AwardEditor();tabs.addTab(self.awards,'Source awards')
        self.checks=QPlainTextEdit();self.checks.setReadOnly(True);tabs.addTab(self.checks,'Checks / source text')
        rl.addWidget(button('Apply edits & check totals',self.apply_edits));splitter.addWidget(right);splitter.setSizes([680,520])

    def load(self,rows,notices,sources):
        self.current=-1;self.rows=copy.deepcopy(rows);self.sources=copy.deepcopy(sources)
        self.notices=notices
        self.message.setText(f'{len(rows)} records awaiting your review. {len(notices)} page-level notes. All values require confirmation; blank cells mean Missing.')
        self.refresh();self.pending.selectRow(0)
        if not rows:
            self.clear_editor();self.set_sources(sources)

    def clear_editor(self):
        for w in self.fields.values():w.clear()
        for w in self.judges.values():w.clear()
        self.notes.clear();self.checks.clear();self.awards.set_awards({})
        for i in range(len(COLUMNS)):
            self.scores.item(i,1).setText('');self.scores.item(i,2).setText('')

    def flush(self):
        if self.current<0 or self.current>=len(self.rows):return
        r=copy.deepcopy(self.rows[self.current])
        for key,w in self.fields.items():r[key]=w.text().strip()
        r['notes']=self.notes.toPlainText();r['judges']={k:w.text().strip() for k,w in self.judges.items() if w.text().strip()}
        r['awards']=self.awards.awards()
        for i,(key,title) in enumerate(COLUMNS):
            for j,category in [(1,'scores'),(2,'ranks')]:
                try:r[category][key]=number(self.scores.item(i,j).text())
                except ValueError:raise ValueError(f'{title}: enter a valid number or leave blank.')
        self.rows[self.current]=r

    def refresh(self):
        self.pending.blockSignals(True)
        fill_table(self.pending,[[r['school'],r['event'],r['date'],r['division'],fmt(r['scores'].get('total')),str(len(warnings(r)))] for r in self.rows])
        self.pending.setColumnWidth(0,240);self.pending.setColumnWidth(1,160);self.pending.setColumnWidth(2,110)
        self.pending.blockSignals(False);self.save_button.setEnabled(bool(self.rows))

    def select_record(self):
        if self.loading:return
        index=self.pending.currentRow()
        if index==self.current or index<0:return
        try:self.flush()
        except ValueError as e:
            self.window.error(str(e));self.pending.blockSignals(True);self.pending.selectRow(self.current);self.pending.blockSignals(False);return
        self.current=index;r=self.rows[index];self.loading=True
        schools=sorted(set(x['school'] for x in self.window.library.records()))
        completer=QCompleter(schools,self);completer.setCaseSensitivity(Qt.CaseInsensitive);completer.setFilterMode(Qt.MatchContains);self.fields['school'].setCompleter(completer)
        for key,w in self.fields.items():w.setText(str(r.get(key,'')))
        for key,w in self.judges.items():w.setText(r.get('judges',{}).get(key,''))
        self.notes.setPlainText(r.get('notes',''))
        self.awards.set_awards(r.get('awards',{}))
        for i,(key,title) in enumerate(COLUMNS):
            for j,category in [(1,'scores'),(2,'ranks')]:
                value=r[category].get(key);self.scores.item(i,j).setText('' if value is None else fmt(value))
        self.checks.setPlainText('\n'.join(warnings(r))+'\n\nOriginal header text:\n'+r.get('header_text',''))
        self.loading=False;self.set_sources(r['sources'])

    def set_sources(self,sources):
        self.source.blockSignals(True);self.source.clear()
        for src in sources:self.source.addItem(f"{src['name']} · page {src['page']}",src)
        self.source.blockSignals(False);self.show_source()

    def show_source(self):
        src=self.source.currentData()
        if not src:return
        self.page.blockSignals(True);self.page.setValue(src['page']);self.page.blockSignals(False)
        try:self.viewer.show_image(load_image(self.window.library.asset_path(src),src['page'],2))
        except Exception as e:self.window.statusBar().showMessage('Preview: '+str(e))

    def change_page(self):
        src=self.source.currentData()
        if not src:return
        try:self.viewer.show_image(load_image(self.window.library.asset_path(src),self.page.value(),2))
        except Exception as e:self.window.statusBar().showMessage(str(e))

    def attach_page(self):
        src=self.source.currentData()
        if src and self.current>=0:
            src=copy.deepcopy(src);src['page']=self.page.value()
            try:load_image(self.window.library.asset_path(src),src['page'],.5)
            except Exception as e:self.window.error(str(e));return
            if src not in self.rows[self.current]['sources']:self.rows[self.current]['sources'].append(src)
            self.window.statusBar().showMessage('Displayed page attached to this draft record.')

    def open_original(self):
        src=self.source.currentData()
        if src:QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.window.library.asset_path(src))))

    def apply_edits(self):
        try:
            self.flush();self.refresh()
            if self.current>=0:
                self.checks.setPlainText('\n'.join(warnings(self.rows[self.current])) or 'No arithmetic or missing-caption checks. Verify against the original.')
                self.pending.blockSignals(True);self.pending.selectRow(self.current);self.pending.blockSignals(False)
            self.window.statusBar().showMessage('Draft updated. Nothing is saved until Confirm & save batch.')
        except Exception as e:self.window.error(str(e))

    def add_record(self):
        try:self.flush()
        except Exception as e:self.window.error(str(e));return
        r=blank_record()
        r['school']=self.window.library.default_school()
        if self.rows:
            for key in ['season','date','event','division','scheme']:r[key]=self.rows[-1][key]
            r['sources']=copy.deepcopy(self.rows[-1]['sources'])
        else:r['sources']=copy.deepcopy(self.sources[:1])
        self.rows.append(r);self.refresh();self.pending.selectRow(len(self.rows)-1)

    def remove_record(self):
        index=self.pending.currentRow()
        if index<0:return
        self.rows.pop(index);self.current=-1;self.refresh();self.clear_editor()
        if self.rows:self.pending.selectRow(min(index,len(self.rows)-1))

    def save_batch(self):
        try:
            self.flush()
            for i,r in enumerate(self.rows):
                try:validate(r)
                except Exception as e:raise ValueError(f'Record {i+1} ({r["school"] or "unnamed"}): {e}')
            counts=self.window.library.preview(self.rows)
            checks=sum(len(warnings(r)) for r in self.rows)
            msg='\n'.join(f'{k.title()}: {v}' for k,v in counts.items())
            msg+=f'\n\n{checks} missing-value or arithmetic checks.\nI have reviewed this batch against the originals. Save confirmed data?'
            if QMessageBox.question(self,'Confirm reviewed batch',msg)!=QMessageBox.Yes:return
            if self.window.library.commit(self.rows,f'Imported {len(self.rows)} reviewed records',self.window.resolve):
                self.rows=[];self.current=-1;self.sources=[];self.refresh();self.clear_editor();self.source.clear();self.viewer.scene().clear()
                self.message.setText('Batch saved. Your confirmed library and charts are up to date.');self.saved.emit()
        except Exception as e:self.window.error(str(e))

class ManagementPage(QWidget):
    def __init__(self,window):
        super().__init__();self.window=window;l=QVBoxLayout(self);l.setContentsMargins(28,22,28,22)
        l.addWidget(label('YOUR WORKSPACE','eyebrow'));l.addWidget(label('Make it yours. Keep it portable.','heading'))
        settings=QGroupBox('Default school');setting_layout=QVBoxLayout(settings)
        help_text=label('Choose the school shown when you open the app. This also fills the school field for manually added records.','muted');help_text.setWordWrap(True);setting_layout.addWidget(help_text)
        controls=QHBoxLayout();self.default_school=QComboBox();self.default_school.setEditable(True)
        self.default_school.setInsertPolicy(QComboBox.NoInsert);controls.addWidget(self.default_school,1)
        controls.addWidget(button('Save default school',self.save_default,True));setting_layout.addLayout(controls);l.addWidget(settings)
        info=label('A .scsboa package contains scores and original files. Share it privately, then review and merge it in the same app.\nThere are no accounts, cloud uploads or automatic background sync.','muted');info.setWordWrap(True);l.addWidget(info)
        bar=QHBoxLayout();self.season=QComboBox();bar.addWidget(label('Export'));bar.addWidget(self.season)
        bar.addWidget(button('Export package with originals',self.export,True));bar.addWidget(button('Import & merge package',window.choose_package));bar.addStretch();l.addLayout(bar)
        l.addWidget(label('Library history','sectionTitle'));self.history=table(['Batch','Description','Saved at (UTC)','Library records']);l.addWidget(self.history,1)
        bar=QHBoxLayout();bar.addWidget(button('Undo latest library change',self.undo));bar.addStretch();l.addLayout(bar)
        storage=label('Local library: '+str(window.library.root),'muted');storage.setWordWrap(True);l.addWidget(storage)
        l.addWidget(label('Undo restores imports or award edits. Your default school is a device preference and stays unchanged.','muted'))
    def refresh(self):
        default=self.window.library.default_school();self.default_school.clear()
        self.default_school.addItems(sorted(set([default]+[school_name(r['school']) for r in self.window.library.records()])))
        self.default_school.setCurrentText(default)
        self.season.clear();self.season.addItem('All seasons');self.season.addItems(sorted(set(r['season'] for r in self.window.library.records())))
        fill_table(self.history,self.window.library.history());self.history.setColumnWidth(1,350);self.history.setColumnWidth(2,260)
    def save_default(self):
        try:
            self.window.library.set_default_school(self.default_school.currentText())
            self.window.refresh_all();self.window.school_page.select_default()
            self.window.statusBar().showMessage('Default school saved. It will be selected when you open the app.')
        except Exception as e:self.window.error(str(e))
    def export(self):
        path,_=QFileDialog.getSaveFileName(self,'Export library','SCSBOA-season.scsboa','SCSBOA package (*.scsboa)')
        if not path:return
        try:
            rows=self.window.library.records()
            if self.season.currentIndex()>0:rows=[r for r in rows if r['season']==self.season.currentText()]
            self.window.library.export_package(path,rows);QMessageBox.information(self,'Export complete',f'{len(rows)} records and their originals exported.\n{path}')
        except Exception as e:self.window.error(str(e))
    def undo(self):
        if not self.window.library.history():return
        if QMessageBox.question(self,'Undo latest library change','Restore records before the latest import or award edit? Originals and device preferences will be retained.')==QMessageBox.Yes:
            self.window.library.undo();self.window.refresh_all()

class MainWindow(QMainWindow):
    def __init__(self,data_dir):
        super().__init__();self.setWindowTitle('SCSBOA Score Studio · '+__version__);self.resize(1480,960);self.setMinimumSize(1100,740)
        self.library=Library(data_dir);self.worker=None;self.setAcceptDrops(True)
        root=QWidget();self.setCentralWidget(root);layout=QHBoxLayout(root);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(225);sl=QVBoxLayout(sidebar);sl.setContentsMargins(17,28,17,22)
        brand=label('SCORE\nSTUDIO');brand.setStyleSheet('font-size:25px;font-weight:800;letter-spacing:2px');sl.addWidget(brand)
        sl.addWidget(label('SCSBOA / FIELD SEASON'));sl.addSpacing(28);self.nav=[]
        for i,(title,kind) in enumerate([('Schools','school'),('Events','event'),('Season overview','season'),('Import & review','import'),('Data Management','settings')]):
            b=button(title,lambda checked=False,index=i:self.navigate(index));b.setIcon(nav_icon(kind));b.setIconSize(QSize(23,23));b.setCheckable(True);sl.addWidget(b);self.nav.append(b)
        sl.addStretch()
        schoolbox=QFrame();schoolbox.setObjectName('sidebarSchool');schoollayout=QVBoxLayout(schoolbox);schoollayout.setContentsMargins(12,13,12,12)
        schoollayout.addWidget(label('YOUR DEFAULT SCHOOL','eyebrow'));self.sidebar_school=label(self.library.default_school());self.sidebar_school.setWordWrap(True);schoollayout.addWidget(self.sidebar_school)
        schoollayout.addWidget(button('Change default',lambda:self.navigate(4)));sl.addWidget(schoolbox);sl.addSpacing(12)
        sl.addWidget(label('OFFLINE LIBRARY · v'+__version__));layout.addWidget(sidebar)
        content=QWidget();cl=QVBoxLayout(content);cl.setContentsMargins(0,0,0,0);self.stack=QStackedWidget();cl.addWidget(self.stack)
        self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.hide();cl.addWidget(self.progress)
        self.cancel=button('Cancel import',self.cancel_import);self.cancel.hide();cl.addWidget(self.cancel);layout.addWidget(content,1)
        self.explorers=[ExplorerPage(self,mode) for mode in ['school','event','season']]
        self.school_page,self.event_page,self.season_page=self.explorers
        for page in self.explorers:self.stack.addWidget(page)
        self.review=ReviewPage(self);self.stack.addWidget(self.review);self.review.saved.connect(self.refresh_all)
        self.management=ManagementPage(self);self.stack.addWidget(self.management);self.refresh_all();self.navigate(0)
        self.statusBar().showMessage('Ready · Offline · Import a recap to begin')

    def navigate(self,index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav):b.setChecked(i==index)
    def error(self,text):QMessageBox.warning(self,'Score Studio',text)
    def refresh_all(self):
        self.sidebar_school.setText(self.library.default_school())
        for page in self.explorers:page.refresh()
        self.management.refresh()
    def resolve(self,old,new,conflicts):
        dialog=ConflictDialog(old,new,conflicts,self)
        return dialog.result_choices() if dialog.exec()==QDialog.Accepted else None
    def replace_draft(self):
        if self.worker and self.worker.isRunning():self.error('An import is already running.');return False
        if self.review.rows:
            return QMessageBox.question(self,'Replace pending batch','Discard the unsaved review batch and import another?')==QMessageBox.Yes
        return True
    def choose_files(self):
        paths,_=QFileDialog.getOpenFileNames(self,'Import SCSBOA recaps','','Recaps (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.heic *.heif)')
        if paths:self.start_import(paths)
    def start_import(self,paths):
        if not self.replace_draft():return
        self.navigate(3);self.progress.show();self.cancel.show();self.review.setEnabled(False)
        self.worker=ImportWorker(paths,self.library);self.worker.progress.connect(self.statusBar().showMessage)
        self.worker.done.connect(self.import_done);self.worker.failed.connect(self.error);self.worker.finished.connect(self.import_finished);self.worker.start()
    def import_done(self,rows,notes,sources):self.review.load(rows,notes,sources)
    def import_finished(self):
        self.progress.hide();self.cancel.hide();self.review.setEnabled(True);self.statusBar().showMessage('Import stopped or finished. Review all fields before saving.');self.worker=None
    def cancel_import(self):
        if self.worker:self.worker.requestInterruption();self.statusBar().showMessage('Cancelling after the current recognition step…')
    def choose_package(self):
        path,_=QFileDialog.getOpenFileName(self,'Import shared package','','SCSBOA package (*.scsboa)')
        if not path or not self.replace_draft():return
        try:
            rows=self.library.read_package(path);sources=[]
            for r in rows:
                for src in r['sources']:
                    if src not in sources:sources.append(src)
            self.review.load(rows,[],sources);self.navigate(3)
        except Exception as e:self.error(str(e))
    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls():event.acceptProposedAction()
    def dropEvent(self,event):
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:self.start_import(paths)
    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption();event.ignore();self.statusBar().showMessage('Stopping local OCR before closing…')
            self.worker.finished.connect(self.close);return
        if self.review.rows and QMessageBox.question(self,'Unsaved review','Discard this unconfirmed batch and close? Saved scores will remain.')!=QMessageBox.Yes:
            event.ignore();return
        self.library.db.close();event.accept()

def main():
    app=QApplication(sys.argv);app.setApplicationName('SCSBOA Score Studio');app.setStyle('Fusion');app.setStyleSheet(STYLE)
    data=os.environ.get('SCORESTUDIO_DATA',str(Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'SCSBOA Score Studio'))
    Path(data).mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(Path(data)/'application.lock'));lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(None,'Score Studio','This library is already open in another Score Studio window.');return 0
    window=MainWindow(data);window.show()
    return app.exec()
