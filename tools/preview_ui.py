import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from scorestudio.app import MainWindow
from scorestudio.widgets import STYLE

app=QApplication([])
for name in ['segoeui.ttf','segoeuib.ttf']:
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setStyle('Fusion');app.setStyleSheet(STYLE)
w=MainWindow('tmp/ui-library');w.show();app.processEvents()
w.grab().save('tmp/ui-overview.png')
w.navigate(3);app.processEvents();w.grab().save('tmp/ui-review.png')
w.library.db.close()
print('UI rendered')
