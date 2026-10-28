"""School profiles, event comparisons and source-backed honors."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFrame,QComboBox,QLineEdit,QSplitter,
                             QScrollArea,QDialog,QDialogButtonBox,QPlainTextEdit,QTabWidget,QHeaderView)
from .model import COLUMNS,LABELS,MAIN,CAPTIONS,normalized,school_name,school_key,leaders
from .ui_common import label,button,table,fill_table,fmt,mark_first,AwardEditor
from .widgets import Chart,SourceView,StatCard,HighlightCard
from .recognition import load_image

class ExplorerPage(QWidget):
    def __init__(self,window,mode):
        super().__init__();self.window=window;self.mode=mode;self.visible=[];self.highlight_data=[];self.chart_targets=[]
        layout=QVBoxLayout(self);layout.setContentsMargins(25,23,25,20);layout.setSpacing(13)
        header=QHBoxLayout();titles=QVBoxLayout();titles.setSpacing(5)
        self.eyebrow=label({'school':'SCHOOL PROFILE','event':'ON THE FIELD','season':'YOUR SEASON'}[mode],'eyebrow');titles.addWidget(self.eyebrow)
        self.heading=label({'school':'Your school, in focus.','event':'Every caption. Every contender.','season':'A season, in perspective.'}[mode],'heading')
        self.heading.setWordWrap(True);titles.addWidget(self.heading)
        self.subtitle=label('Explore reviewed scores, source rankings and recorded awards.','muted');self.subtitle.setWordWrap(True);titles.addWidget(self.subtitle)
        header.addLayout(titles,1);header.addWidget(button('Import recap',lambda:window.navigate(3),True),0,Qt.AlignTop);layout.addLayout(header)
        filterbox=QFrame();filterbox.setObjectName('surface');fl=QVBoxLayout(filterbox);fl.setContentsMargins(12,10,12,10);fl.setSpacing(8)
        first=QHBoxLayout()
        self.selector=QComboBox();self.selector.setMinimumWidth(220);self.selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon);self.selector.setMinimumContentsLength(18)
        if mode!='season':first.addWidget(self.selector,1)
        self.metric=QComboBox();self.metric.setMinimumWidth(185)
        for key,title in COLUMNS:self.metric.addItem(title,key)
        self.metric.setCurrentIndex([k for k,t in COLUMNS].index('total'));first.addWidget(self.metric,1);fl.addLayout(first)
        second=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Filter visible results…');second.addWidget(self.search,1)
        self.season_filter=QComboBox();self.season_filter.setMinimumWidth(240)
        self.season_filter.setToolTip('Select a season and its scoring system together. Different scoring systems stay separate.')
        second.addWidget(label('Season / scoring','muted'));second.addWidget(self.season_filter);fl.addLayout(second);layout.addWidget(filterbox)
        stats=QHBoxLayout();stats.setSpacing(12);self.cards=[StatCard('Latest score'),StatCard('Appearances')]
        if mode=='season':self.cards.append(StatCard('Events'))
        for card in self.cards:stats.addWidget(card,1)
        layout.addLayout(stats)
        split=QSplitter();split.setChildrenCollapsible(False);left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,0,0);ll.setSpacing(10)
        self.vertical_split=QSplitter(Qt.Vertical);self.vertical_split.setChildrenCollapsible(False);ll.addWidget(self.vertical_split,1)
        self.chart=Chart();self.chart.activated.connect(self.chart_clicked);chart_scroll=QScrollArea();chart_scroll.setWidgetResizable(True);chart_scroll.setWidget(self.chart)
        chart_scroll.setMinimumHeight(160);self.vertical_split.addWidget(chart_scroll)
        self.caption=label('Gold highlights indicate rank #1 in the reviewed source.','muted');self.caption.setWordWrap(True)
        controls=QHBoxLayout();controls.addWidget(self.caption,1);controls.addWidget(button('Expand chart',self.expand_chart));ll.addLayout(controls)
        self.grid=table(['School','Event','Date','Division','Final','Selected','Rank','Gap'])
        self.grid.setMinimumHeight(85);self.grid.cellClicked.connect(self.detail);self.vertical_split.addWidget(self.grid)
        self.vertical_split.setStretchFactor(0,65);self.vertical_split.setStretchFactor(1,35);self.vertical_split.setSizes([390,180])
        tip=label('Click a point, bar or result for details. Drag the divider to resize.','muted');ll.addWidget(tip)
        split.addWidget(left)
        self.honors=QScrollArea();self.honors.setWidgetResizable(True);self.honors.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.honors.setMinimumWidth(245);self.honors.setMaximumWidth(360)
        self.honors_body=QWidget();self.honors_layout=QVBoxLayout(self.honors_body);self.honors_layout.setContentsMargins(8,0,0,0);self.honors_layout.setSpacing(10)
        self.honors.setWidget(self.honors_body);split.addWidget(self.honors);split.setStretchFactor(0,4);split.setStretchFactor(1,1)
        split.setSizes([800,290]);layout.addWidget(split,1)
        if mode!='school':self.honors.hide()
        if mode=='season':self.metric.hide()
        self.season_filter.currentIndexChanged.connect(self.refresh_choices)
        self.selector.currentIndexChanged.connect(self.render);self.metric.currentIndexChanged.connect(self.render);self.search.textChanged.connect(self.render)

    def refresh(self):
        records=self.window.library.records()
        pairs=sorted({('2026','scsboa-field-2026')}|{(r['season'],r['scheme']) for r in records})
        old=self.season_filter.currentData();self.season_filter.blockSignals(True);self.season_filter.clear()
        for season,scheme in pairs:
            title=f'{season} · SCSBOA Field' if scheme==f'scsboa-field-{season}' else f'{season} · {scheme}'
            self.season_filter.addItem(title,(season,scheme))
        index=self.season_filter.findData(old)
        self.season_filter.setCurrentIndex(max(0,index));self.season_filter.blockSignals(False)
        self.refresh_choices()

    def filtered(self):
        selected=tuple(self.season_filter.currentData() or ('2026','scsboa-field-2026'))
        return [r for r in self.window.library.records() if (r['season'],r['scheme'])==selected]

    def refresh_choices(self):
        records=self.filtered();old=self.selector.currentData();self.selector.blockSignals(True);self.selector.clear()
        if self.mode=='school':
            default=self.window.library.default_school()
            names=sorted(set([school_name(r['school']) for r in records]+[default]))
            for name in names:self.selector.addItem(name,school_key(name))
            target=old if old is not None else school_key(default)
            index=self.selector.findData(target)
            self.selector.setCurrentIndex(index if index>=0 else self.selector.findData(school_key(default)))
        elif self.mode=='event':
            for event in sorted(set((r['date'],r['event'],r['division']) for r in records)):
                self.selector.addItem(' · '.join(event),event)
            index=self.selector.findData(old)
            if index>=0:self.selector.setCurrentIndex(index)
        self.selector.blockSignals(False);self.render()

    def select_default(self):
        if self.mode=='school':
            self.refresh_choices();self.selector.setCurrentIndex(self.selector.findData(school_key(self.window.library.default_school())))

    def render(self):
        scoped=self.filtered();metric=self.metric.currentData() or 'total'
        if self.mode=='school':
            scoped=[r for r in scoped if school_key(r['school'])==self.selector.currentData()]
            self.heading.setText(self.selector.currentText() or 'Your school, in focus.')
            is_default=self.selector.currentData()==school_key(self.window.library.default_school())
            self.eyebrow.setText('YOUR DEFAULT SCHOOL' if is_default else 'SCHOOL PROFILE')
            self.subtitle.setText('Season '+str((self.season_filter.currentData() or ('2026',))[0])+' · Confirmed results and source-backed honors')
        elif self.mode=='event':
            scoped=[r for r in scoped if (r['date'],r['event'],r['division'])==tuple(self.selector.currentData() or ())]
            self.subtitle.setText(self.selector.currentText() or 'Choose a reviewed event and official division.')
        scoped.sort(key=lambda r:(r['date'],r['event'],r['division'],r['school']))
        search=normalized(self.search.text())
        records=[r for r in scoped if search in normalized(' '.join([school_name(r['school']),r['event'],r['division']]))]
        if self.mode=='event':records.sort(key=lambda r:-(r['scores'].get(metric) if r['scores'].get(metric) is not None else -1e9))
        self.visible=records;values=[r['scores'][metric] for r in scoped if r['scores'].get(metric) is not None];highest=max(values) if values else None
        fill_table(self.grid,[[school_name(r['school']),r['event'],r['date'],r['division'],fmt(r['scores'].get('total')),fmt(r['scores'].get(metric)),
            '1st' if r['ranks'].get(metric)==1 else fmt(r['ranks'].get(metric)),
            fmt(highest-r['scores'][metric]) if self.mode=='event' and highest is not None and r['scores'].get(metric) is not None else '—'] for r in records])
        for col,width in enumerate([230,115,100,65,65,75,55,60]):self.grid.setColumnWidth(col,width)
        self.grid.setColumnHidden(1,self.mode=='event');self.grid.setColumnHidden(2,self.mode=='event');self.grid.setColumnHidden(3,self.mode=='event')
        self.grid.setColumnHidden(7,self.mode!='event')
        for i,r in enumerate(records):
            if r['ranks'].get(metric)==1:mark_first(self.grid,i,[0,5,6])
        first=[i for i,r in enumerate(records) if r['ranks'].get(metric)==1]
        events=len(set((r['date'],r['event']) for r in scoped));schools=len(set(school_key(r['school']) for r in scoped))
        self.chart_targets=list(records)
        if self.mode=='school':
            recent=next((r for r in reversed(scoped) if r['scores'].get(metric) is not None),None)
            self.cards[0].set_content('Latest '+('total' if metric=='total' else 'score'),fmt(recent['scores'][metric]) if recent else '—',recent['date'] if recent else 'Awaiting a reviewed result')
            self.cards[1].set_content('Appearances',len(scoped),f'{events} imported events')
            self.chart.set_data([(r['date'][5:]+' · '+r['event']+' · '+r['division'],r['scores'].get(metric)) for r in records],'line',LABELS[metric]+' · season trend',first)
            self.caption.setText('Gold points = source rank #1. Missing scores remain gaps.')
        elif self.mode=='event':
            self.cards[0].set_content('Highest imported',fmt(highest) if highest is not None else '—',LABELS[metric])
            self.cards[1].set_content('Schools',schools,'Same event · same division')
            self.chart.set_data([(school_name(r['school']),r['scores'].get(metric)) for r in records],'bar',LABELS[metric]+' · division comparison',first)
            self.caption.setText(f'Spread: {max(values)-min(values):.3f} · Gold indicates source rank #1; gaps use the full imported group.' if values else 'No scores for the selected metric.')
        else:
            self.cards[0].set_content('Reviewed results',len(scoped),'Saved on this device')
            self.cards[1].set_content('Schools',schools,'Across imported divisions')
            self.cards[2].set_content('Events',events,'Imported coverage only')
            eventlist=sorted(set((r['date'],r['event']) for r in records))
            self.chart_targets=eventlist
            self.chart.set_data([(date[5:]+' '+name,len({school_key(r['school']) for r in scoped if (r['date'],r['event'])==(date,name)})) for date,name in eventlist],'bar','Coverage · imported schools per event')
            self.caption.setText('Coverage reflects your imports, not a complete official season schedule.')
        self.render_highlights(scoped)

    def render_highlights(self,records):
        while self.honors_layout.count():
            item=self.honors_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.highlight_data=[]
        if self.mode!='school':return
        self.honors_layout.addWidget(label('Awards & highlights','sectionTitle'))
        award_count=0
        for r in reversed(records):
            context=f"{r['event']} · {r['date']} · {r['division']}"
            for name,evidence in r.get('awards',{}).items():
                self.honors_layout.addWidget(HighlightCard('RECORDED AWARD',name,context+'\n'+evidence,True));award_count+=1
        if not award_count:self.honors_layout.addWidget(HighlightCard('RECORDED AWARDS','No named awards recorded','Open a result to add awards explicitly listed in the source.'))
        for r in reversed(records):
            captions=[CAPTIONS[k] for k in MAIN if r['ranks'].get(k)==1]
            if captions:
                self.honors_layout.addWidget(HighlightCard('SOURCE RANK #1',' · '.join(captions),f"{r['event']} · {r['date']} · {r['division']}",True))
        self.honors_layout.addStretch()

    def chart_clicked(self,index):
        if not 0<=index<len(self.chart_targets):return
        target=self.chart_targets[index]
        if self.mode=='season':self.show_event(target)
        else:self.show_record(target)

    def expand_chart(self):
        dialog=QDialog(self);dialog.setWindowTitle('Expanded chart');dialog.resize(1250,820)
        layout=QVBoxLayout(dialog);scroll=QScrollArea();scroll.setWidgetResizable(True)
        chart=Chart();chart.setMinimumHeight(450)
        chart.set_data(self.chart.points,self.chart.mode,self.chart.title,self.chart.first_indices)
        targets=list(self.chart_targets)
        chart.activated.connect(lambda i:self.show_event(targets[i]) if self.mode=='season' else self.show_record(targets[i]))
        scroll.setWidget(chart);layout.addWidget(scroll,1)
        layout.addWidget(label('Click a point or bar for details. Scroll horizontally for more results.','muted'))
        layout.addWidget(button('Close',dialog.accept));dialog.exec()

    def show_event(self,event):
        records=[r for r in self.filtered() if (r['date'],r['event'])==tuple(event)]
        dialog=QDialog(self);dialog.setWindowTitle('Event rankings');dialog.resize(1100,760)
        layout=QVBoxLayout(dialog);layout.addWidget(label(event[1],'heading'))
        layout.addWidget(label(event[0]+' · Imported results only · '+str(len({school_key(r['school']) for r in records}))+' schools','muted'))
        metric=QComboBox()
        for key,title in COLUMNS:metric.addItem(title,key)
        metric.setCurrentIndex(metric.findData('total'));layout.addWidget(metric)
        grid=table(['Division','School','Score','Source rank','Imported order']);grid.setObjectName('eventRankings');layout.addWidget(grid,1)
        displayed=[]
        def render():
            key=metric.currentData();displayed.clear();rows=[];previous_division=None;previous_score=None;rank=0;position=0
            for r in sorted(records,key=lambda r:(r['division'],r['scores'].get(key) is None,-(r['scores'].get(key) or 0),school_key(r['school']))):
                score=r['scores'].get(key)
                if r['division']!=previous_division:position=0;previous_score=None
                position+=1
                if score!=previous_score or position==1:rank=position
                rows.append([r['division'],school_name(r['school']),fmt(score),fmt(r['ranks'].get(key)),str(rank) if score is not None else '—'])
                displayed.append(r);previous_division=r['division'];previous_score=score
            fill_table(grid,rows);grid.setColumnWidth(0,100);grid.setColumnWidth(1,410)
            for i,r in enumerate(displayed):
                if r['ranks'].get(key)==1:mark_first(grid,i,[1,2,3])
        metric.currentIndexChanged.connect(render);render()
        grid.cellClicked.connect(lambda row,col:self.show_record(displayed[row]))
        layout.addWidget(label('Each division is sorted separately. Imported order is not an official placement. Click a school for all scores.','muted'))
        layout.addWidget(button('Close',dialog.accept));dialog.exec()

    def detail(self,row,col):
        if row<0 or row>=len(self.visible):return
        self.show_record(self.visible[row])

    def show_record(self,r):
        dialog=QDialog(self);dialog.resize(1180,760);dialog.setWindowTitle(school_name(r['school'])+' · Score details')
        layout=QVBoxLayout(dialog);layout.addWidget(label(school_name(r['school']),'heading'))
        layout.addWidget(label(f"{r['event']} · {r['date']} · {r['division']} · Original: {r.get('original_school') or r['school']}",'muted'))
        tabs=QTabWidget();layout.addWidget(tabs,1);scores=table(['Caption','Score','Source rank'])
        fill_table(scores,[[title,fmt(r['scores'].get(key)),'1st' if r['ranks'].get(key)==1 else fmt(r['ranks'].get(key))] for key,title in COLUMNS])
        scores.setColumnWidth(0,480);scores.setObjectName('detailScores')
        layout.insertWidget(2,label('Final total: '+fmt(r['scores'].get('total')),'sectionTitle'))
        for i,(key,title) in enumerate(COLUMNS):
            if r['ranks'].get(key)==1:mark_first(scores,i,[0,1,2])
            for col in (0,1):
                font=scores.item(i,col).font();font.setBold(key in MAIN);scores.item(i,col).setFont(font)
        tabs.addTab(scores,'Scores && ranks');editor=AwardEditor();editor.set_awards(r.get('awards',{}));tabs.addTab(editor,'Source awards')
        container=QWidget();cl=QVBoxLayout(container);combo=QComboBox();cl.addWidget(combo);view=SourceView();cl.addWidget(view,1)
        for src in r['sources']:combo.addItem(f"{src['name']} · page {src['page']}",src)
        def show():
            src=combo.currentData()
            if src:
                try:view.show_image(load_image(self.window.library.asset_path(src),src['page'],2))
                except Exception as e:self.window.error(str(e))
        combo.currentIndexChanged.connect(show);cl.addWidget(button('Fit original',view.fit));tabs.insertTab(1,container,'Original');tabs.currentChanged.connect(lambda i:show() if i==1 else None);show()
        notes=QPlainTextEdit();notes.setReadOnly(True);notes.setMaximumHeight(70)
        notes.setPlainText('Judges: '+', '.join(f'{k}: {v}' for k,v in r['judges'].items())+'\n'+r.get('notes',''));layout.addWidget(notes)
        actions=QHBoxLayout();actions.addWidget(label('Award edits are included in packages and can be undone in Data Management.','muted'));actions.addStretch()
        def save():
            try:self.window.library.update_awards(r,editor.awards());self.window.refresh_all();dialog.accept()
            except Exception as e:self.window.error(str(e))
        actions.addWidget(button('Close',dialog.reject));actions.addWidget(button('Save award changes',save,True));layout.addLayout(actions);dialog.exec()
