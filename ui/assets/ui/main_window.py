python -c "
content = '''from PyQt5.QtWidgets import QMainWindow, QLabel
from PyQt5.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(\"Attendance System\")
        self.setMinimumSize(1000, 650)
        label = QLabel(\"Phase 1 Complete — UI coming in Phase 6\", self)
        label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(label)
'''
with open('ui/main_window.py', 'w') as f:
    f.write(content)
print('main_window.py written.')
"