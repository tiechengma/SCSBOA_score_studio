"""Explicit local install verification; never runs on normal launch."""
import json
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from .app import MainWindow
from .widgets import STYLE
from .recognition import Recognizer,load_image

def verify(output,sample=None):
    root=Path(output);root.mkdir(parents=True,exist_ok=True);report={}
    try:
        app=QApplication([])
        for font in ['segoeui.ttf','segoeuib.ttf']:QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+font)
        app.setStyle('Fusion');app.setStyleSheet(STYLE)
        window=MainWindow(root/'library');window.show();app.processEvents()
        window.grab().save(str(root/'window.png'));report['qt_window']=True
        engine=Recognizer();report['offline_models']=True
        from pdfminer.cmapdb import CMapDB
        CMapDB.get_cmap('UniJIS-UTF16-H');report['safe_json_cmaps']=True
        if sample:
            src=window.library.stage_source(sample)
            rows,notes,ctx=engine.parse(load_image(sample),src)
            report['recognized_records']=len(rows);report['totals']=[r['scores'].get('total') for r in rows]
            window.review.load(rows,notes,[src]);window.navigate(3);app.processEvents()
            window.grab().save(str(root/'review.png'))
            report['pending_not_saved']=len(window.library.records())==0
        window.library.db.close()
    except Exception as e:
        import traceback
        report['error']=str(e);report['traceback']=traceback.format_exc()
    (root/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return 1 if 'error' in report else 0
