"""Native Qt display widgets; charts deliberately preserve gaps."""
from PySide6.QtCore import Qt,QRectF,QPointF,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QFont,QPixmap,QImage,QIcon
from PySide6.QtWidgets import QWidget,QGraphicsView,QGraphicsScene,QFrame,QVBoxLayout,QLabel
from PIL.ImageQt import ImageQt

class SourceView(QGraphicsView):
    def __init__(self):
        super().__init__(); self.setScene(QGraphicsScene(self)); self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor('#e5e9ef')); self.setMinimumHeight(220)
    def show_image(self,image):
        self.scene().clear(); self.scene().addPixmap(QPixmap.fromImage(ImageQt(image)))
        self.fit()
    def fit(self):
        self.fitInView(self.scene().itemsBoundingRect(),Qt.KeepAspectRatio)
    def wheelEvent(self,event):
        self.scale(1.2 if event.angleDelta().y()>0 else 1/1.2,1.2 if event.angleDelta().y()>0 else 1/1.2)

class StatCard(QFrame):
    def __init__(self,title,value='—',detail='',gold=False):
        super().__init__();self.setObjectName('goldStat' if gold else 'statCard')
        layout=QVBoxLayout(self);layout.setContentsMargins(18,13,18,13);layout.setSpacing(4)
        self.title=QLabel(title.upper());self.title.setObjectName('cardLabel')
        self.value=QLabel(value);self.value.setObjectName('cardValue')
        self.detail=QLabel(detail);self.detail.setObjectName('muted')
        for w in (self.title,self.value,self.detail):w.setTextFormat(Qt.PlainText);layout.addWidget(w)
    def set_content(self,title,value,detail):
        self.title.setText(title.upper());self.value.setText(str(value));self.detail.setText(detail)

class HighlightCard(QFrame):
    def __init__(self,eyebrow,title,detail,gold=False):
        super().__init__();self.setObjectName('goldHighlight' if gold else 'highlightCard')
        layout=QVBoxLayout(self);layout.setContentsMargins(14,12,14,12);layout.setSpacing(5)
        for text,name in [(eyebrow,'goldEyebrow' if gold else 'eyebrow'),(title,'highlightTitle'),(detail,'muted')]:
            w=QLabel(text);w.setTextFormat(Qt.PlainText);w.setWordWrap(True);w.setObjectName(name);layout.addWidget(w)

def nav_icon(kind):
    pm=QPixmap(28,28);pm.fill(Qt.transparent);p=QPainter(pm);p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor('#c5d7e3'),1.7,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin))
    if kind=='school':
        p.drawLine(5,11,14,5);p.drawLine(14,5,23,11);p.drawLine(5,23,23,23)
        for x in [8,14,20]:p.drawLine(x,12,x,22)
    elif kind=='event':
        p.drawRoundedRect(QRectF(5,7,18,17),3,3);p.drawLine(5,13,23,13)
        for x in [10,18]:p.drawLine(x,4,x,10)
        p.drawEllipse(QPointF(14,18),1.4,1.4)
    elif kind=='season':
        p.drawLine(5,23,23,23)
        for x,h in [(8,7),(14,12),(20,18)]:p.drawRoundedRect(QRectF(x-1,23-h,3,h),1,1)
    elif kind=='import':
        p.drawLine(14,4,14,17);p.drawLine(9,12,14,17);p.drawLine(19,12,14,17)
        p.drawLine(5,18,5,23);p.drawLine(5,23,23,23);p.drawLine(23,23,23,18)
    else:
        for y in [7,14,21]:
            p.drawLine(5,y,23,y);p.setBrush(QColor('#142a3b'));p.drawEllipse(QPointF(10 if y!=14 else 18,y),2.5,2.5)
    p.end();return QIcon(pm)

class Chart(QWidget):
    activated=Signal(int)
    def __init__(self):
        super().__init__(); self.points=[]; self.mode='line'; self.title=''; self.setMinimumHeight(160);self.first_indices=set();self.setMouseTracking(True);self.hit_regions=[];self.press_pos=None;self.hovered=-1
    def set_data(self,points,mode,title,first_indices=None):
        self.hit_regions=[];self.points=points; self.mode=mode; self.title=title;self.first_indices=set(first_indices or []); self.setMinimumWidth(max(320,len(points)*135+100)); self.update()
    def hit_index(self,pos):
        return next((i for i,rect in self.hit_regions if rect.contains(pos)),-1)
    def mouseMoveEvent(self,event):
        index=self.hit_index(event.position());self.hovered=index
        self.setCursor(Qt.PointingHandCursor if index>=0 else Qt.ArrowCursor)
        if index>=0:
            name,value=self.points[index];self.setToolTip(name+' · '+('Missing' if value is None else f'{value:g}')+' · Click for details')
        else:self.setToolTip('')
        self.update();super().mouseMoveEvent(event)
    def leaveEvent(self,event):
        self.hovered=-1;self.update();super().leaveEvent(event)
    def mousePressEvent(self,event):
        self.press_pos=event.position() if event.button()==Qt.LeftButton else None
        super().mousePressEvent(event)
    def mouseReleaseEvent(self,event):
        index=self.hit_index(event.position())
        if event.button()==Qt.LeftButton and self.press_pos is not None and (event.position()-self.press_pos).manhattanLength()<6 and index>=0 and self.hit_index(self.press_pos)==index:
            self.press_pos=None;self.activated.emit(index)
        self.press_pos=None;super().mouseReleaseEvent(event)
    def paintEvent(self,event):
        self.hit_regions=[]
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor('#e1e9ed'),1));p.setBrush(QColor('white'));p.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),12,12)
        p.setPen(QColor('#18283f')); p.setFont(QFont('Segoe UI',14,QFont.DemiBold))
        p.drawText(22,30,self.title or 'Score overview')
        values=[v for label,v in self.points if v is not None]
        if not values:
            p.setFont(QFont('Segoe UI',11)); p.setPen(QColor('#45566d'))
            p.drawText(self.rect(),Qt.AlignCenter,'Your confirmed scores will appear here.\nImport a recap to begin.'); return
        if self.first_indices:
            p.setPen(QColor('#9a681a'));p.setFont(QFont('Segoe UI',11));p.drawText(22,49,'GOLD · Source rank #1 (ties included)')
        left,top,width,height=72,76,max(100,self.width()-100),max(40,self.height()-140)
        low=min(0,int(min(values)//5*5)) if self.mode=='bar' else (max(0,int(min(values)//5*5)-5) if min(values)>=0 else int(min(values)//5*5)-5)
        high=max(low+10,(int(max(values)//5)+2)*5)
        p.setFont(QFont('Segoe UI',12))
        ticks=4 if height>=110 else 2 if height>=60 else 1
        for i in range(ticks+1):
            y=top+height*i/ticks; v=high-(high-low)*i/ticks
            p.setPen(QColor('#edf0f5')); p.drawLine(QPointF(left,y),QPointF(left+width,y))
            p.setPen(QColor('#45566d')); p.drawText(QRectF(2,y-12,62,26),Qt.AlignRight,f'{v:g}')
        n=len(self.points); previous=None
        step=width/max(n,1); label_every=1
        for i,(label,value) in enumerate(self.points):
            x=left+step*(i+.5)
            color=QColor('#bd8b31' if i in self.first_indices else '#238b8a')
            if i==self.hovered:color=color.lighter(120)
            if value is None: previous=None
            else:
                y=top+height*(high-value)/(high-low)
                if self.mode=='bar':
                    zero=top+height*high/(high-low)
                    self.hit_regions.append((i,QRectF(x-step*.3,min(y,zero),step*.6,max(1,abs(zero-y))).adjusted(-5,-6,5,6)))
                    p.setPen(Qt.NoPen); p.setBrush(color); p.drawRoundedRect(QRectF(x-step*.3,min(y,zero),step*.6,max(1,abs(zero-y))),5,5)
                else:
                    self.hit_regions.append((i,QRectF(x-14,y-14,28,28)))
                    p.setPen(QPen(QColor('#187e83'),2.5))
                    if previous is not None: p.drawLine(previous,QPointF(x,y))
                    p.setPen(QPen(QColor('white'),2));p.setBrush(color); p.drawEllipse(QPointF(x,y),7,7); previous=QPointF(x,y)
                p.setFont(QFont('Segoe UI',13,QFont.DemiBold));p.setPen(QColor('#18283f')); p.drawText(QRectF(x-50,y-28,100,25),Qt.AlignCenter,f'{value:.3f}'.rstrip('0').rstrip('.'))
            if i%label_every==0:
                p.setFont(QFont('Segoe UI',11));p.setPen(QColor('#35465c')); short=p.fontMetrics().elidedText(label,Qt.ElideRight,int(step)-10)
                p.drawText(QRectF(x-step/2,top+height+8,step*label_every,30),Qt.AlignHCenter|Qt.TextWordWrap,short)
        p.end()

STYLE='''
QMainWindow,QDialog {background:#f4f7f8;color:#18283f;}
QWidget {font-family:"Segoe UI";font-size:13px;color:#18283f;}
QFrame#sidebar {background:#142a3b;} QFrame#sidebar QLabel {color:#d9e5ec;}
QFrame#sidebar QPushButton {background:transparent;color:#c5d7e3;border:0;text-align:left;padding:12px 13px;border-radius:8px;}
QFrame#sidebar QPushButton:hover {background:#203c4e;}
QFrame#sidebar QPushButton:checked {background:#28495a;color:white;border-left:3px solid #d8b56a;font-weight:600;}
QFrame#sidebarSchool {background:#1c3547;border:1px solid #2c4759;border-radius:10px;}
QLabel#heading {font-size:27px;font-weight:700;} QLabel#muted {color:#697b92;}
QLabel#eyebrow {font-size:10px;font-weight:700;color:#278482;letter-spacing:1px;}
QLabel#goldEyebrow {font-size:10px;font-weight:700;color:#9a681a;letter-spacing:1px;}
QLabel#sectionTitle {font-size:15px;font-weight:600;color:#243e50;}
QLabel#highlightTitle {font-size:13px;font-weight:600;}
QLabel#cardLabel {font-size:10px;font-weight:600;color:#728691;letter-spacing:1px;}
QLabel#cardValue {font-size:28px;font-weight:700;color:#163f50;}
QFrame#statCard,QFrame#surface {background:white;border:1px solid #e1e9ed;border-radius:11px;}
QFrame#goldStat {background:#fff8e9;border:1px solid #eddbb5;border-radius:11px;}
QFrame#goldStat QLabel#cardValue {color:#9a681a;}
QFrame#highlightCard {background:white;border:1px solid #e1e9ed;border-radius:10px;}
QFrame#goldHighlight {background:#fff8e9;border:1px solid #eddbb5;border-radius:10px;}
QLabel#stat {font-size:24px;font-weight:700;color:#187e83;padding:12px;background:white;border-radius:8px;}
QPushButton {background:white;border:1px solid #d8e0eb;border-radius:6px;padding:8px 13px;}
QPushButton:hover {background:#eaf3f4;} QPushButton:disabled {color:#9aa7b8;background:#edf0f5;}
QPushButton#primary {background:#187e83;color:white;border:0;font-weight:600;}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit {background:white;border:1px solid #d8e0eb;border-radius:5px;padding:6px;}
QTableWidget {background:white;alternate-background-color:#f8fafb;border:1px solid #e1e9ed;border-radius:8px;selection-background-color:#dceeea;selection-color:#163a49;}
QTableWidget::item {padding:5px;border-bottom:1px solid #eef2f4;}
QHeaderView::section {background:#eef3f5;padding:10px 8px;border:0;font-size:11px;font-weight:600;color:#627886;}
QTabWidget::pane {border:1px solid #dbe4e8;background:white;border-radius:6px;}
QTabBar::tab {padding:10px 13px;color:#71838e;background:transparent;border-bottom:2px solid transparent;}
QTabBar::tab:selected {color:#1f7978;border-bottom:2px solid #238b8a;font-weight:600;}
QGroupBox {border:1px solid #d8e0eb;border-radius:6px;margin-top:12px;padding-top:12px;}
QGroupBox::title {subcontrol-origin:margin;left:10px;} QSplitter::handle {background:#e0e6ee;}
QProgressBar {border:0;background:#e0e6ee;height:6px;} QProgressBar::chunk {background:#187e83;}
QScrollArea {background:transparent;border:0;} QScrollArea>QWidget>QWidget {background:transparent;}
QStatusBar {background:#edf3f5;color:#71838e;font-size:11px;}
QScrollBar:vertical {background:#f0f4f5;width:10px;margin:0;}
QScrollBar::handle:vertical {background:#bdcdd4;border-radius:5px;min-height:30px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
'''
