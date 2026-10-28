"""Shared native controls and source-award editing."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QLabel,QPushButton,QTableWidget,QTableWidgetItem,QAbstractItemView,
                             QWidget,QVBoxLayout,QHBoxLayout)
from .model import validate_awards,normalized

def label(text,name=None):
    w=QLabel(text);w.setTextFormat(Qt.PlainText)
    if name:w.setObjectName(name)
    return w

def button(text,callback,primary=False):
    b=QPushButton(text.replace('&','&&'));b.clicked.connect(callback);b.setCursor(Qt.PointingHandCursor)
    if primary:b.setObjectName('primary')
    return b

def table(headers):
    t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers)
    t.setAlternatingRowColors(True);t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection);t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setShowGrid(False);t.verticalHeader().hide();t.verticalHeader().setDefaultSectionSize(37)
    t.horizontalHeader().setStretchLastSection(True);t.setWordWrap(False)
    return t

def fill_table(t,rows):
    t.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,value in enumerate(row):
            item=QTableWidgetItem(str(value));item.setToolTip(str(value));t.setItem(i,j,item)

def fmt(v):return 'Missing' if v is None else f'{v:.3f}'.rstrip('0').rstrip('.')

def mark_first(t,row,columns):
    for column in columns:
        item=t.item(row,column)
        if item:
            item.setBackground(QColor('#fff1ce'));item.setForeground(QColor('#805416'))
            font=item.font();font.setBold(True);item.setFont(font)
            item.setToolTip(item.toolTip()+'\nFirst place as listed in the source. Ties share the highlight.')

class AwardEditor(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        note=label('Enter awards explicitly named in the source, with a page or wording in the source note. First-place score badges appear automatically from reviewed ranks.','muted')
        note.setWordWrap(True);layout.addWidget(note)
        self.grid=table(['Award name','Source note'])
        self.grid.setEditTriggers(QAbstractItemView.DoubleClicked|QAbstractItemView.EditKeyPressed|QAbstractItemView.AnyKeyPressed)
        self.grid.setColumnWidth(0,200);self.grid.setMinimumHeight(150);layout.addWidget(self.grid,1)
        actions=QHBoxLayout();actions.addWidget(button('Add award',self.add));actions.addWidget(button('Remove selected',self.remove));actions.addStretch();layout.addLayout(actions)
    def set_awards(self,awards):fill_table(self.grid,sorted(awards.items()))
    def add(self):
        row=self.grid.rowCount();self.grid.insertRow(row)
        for col in range(2):self.grid.setItem(row,col,QTableWidgetItem(''))
        self.grid.setCurrentCell(row,0);self.grid.editItem(self.grid.item(row,0))
    def remove(self):
        if self.grid.currentRow()>=0:self.grid.removeRow(self.grid.currentRow())
    def awards(self):
        result={};seen=set()
        for row in range(self.grid.rowCount()):
            name,evidence=[self.grid.item(row,col).text().strip() if self.grid.item(row,col) else '' for col in range(2)]
            if not name and not evidence:continue
            if normalized(name) in seen:raise ValueError('Each award should appear only once.')
            result[name]=evidence;seen.add(normalized(name))
        validate_awards(result);return result
