import sys
import os
import subprocess

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QLineEdit,
    QFileDialog, QProgressBar, QMessageBox,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPixmap, QFont, QColor, QCursor, QIcon
from PySide6.QtCore import Qt, QThread, Signal

from core import process_input


# ---------------- BASE DIR ---------------- #

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)


# ---------------- Worker Thread ---------------- #

class Worker(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, input_path, output_path):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self._is_cancelled:
                return

            result = process_input(
                self.input_path,
                self.output_path,
                self.progress.emit,
                lambda: self._is_cancelled
            )

            if not self._is_cancelled:
                self.finished.emit(result)

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


# ---------------- Main Window ---------------- #

class MainWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Vocardist")
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR, "icon.jpg")))
        self.setFixedSize(920, 620)

        # Background
        self.bg_label = QLabel(self)
        self.bg_label.setGeometry(0, 0, 920, 620)
        self.update_background()

        # Glass panel
        self.panel = QWidget(self)
        self.panel.setFixedSize(540, 440)
        self.panel.move(190, 90)

        self.panel.setStyleSheet("""
            QWidget {
                background: rgba(255,255,255,35);
                border-radius: 14px;
                border: 1px solid rgba(5,5,5,60);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setYOffset(15)
        shadow.setColor(QColor(0,0,0,120))
        self.panel.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.panel)
        layout.setSpacing(18)
        layout.setContentsMargins(50,35,50,35)

        # Input
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Select input file")
        layout.addWidget(self.input_edit)

        self.input_btn = QPushButton("Browse")
        self.input_btn.clicked.connect(self.browse_input)
        self.input_btn.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(self.input_btn)

        # Output
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Select output folder")
        layout.addWidget(self.output_edit)

        out_row = QHBoxLayout()

        self.browse_out = QPushButton("Browse")
        self.browse_out.clicked.connect(self.browse_output)
        self.browse_out.setCursor(QCursor(Qt.PointingHandCursor))
        out_row.addWidget(self.browse_out)

        self.open_btn = QPushButton("📁")
        self.open_btn.setFixedWidth(45)
        self.open_btn.clicked.connect(self.open_output)
        self.open_btn.setCursor(QCursor(Qt.PointingHandCursor))
        out_row.addWidget(self.open_btn)

        layout.addLayout(out_row)

        # Process
        self.process_btn = QPushButton("Remove Vocals")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setCursor(QCursor(Qt.PointingHandCursor))
        layout.addWidget(self.process_btn)

        # Cancel
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        layout.addWidget(self.cancel_btn)

        # Progress
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.status = QLabel("Idle")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:white;")
        layout.addWidget(self.status)

        self.apply_styles()

    # ---------------- Background ---------------- #

    def update_background(self):
        pixmap = QPixmap(
            os.path.join(BASE_DIR, "theme.jpg")
        ).scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation
        )
        self.bg_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        self.update_background()
        super().resizeEvent(event)

    # ---------------- Styles ---------------- #

    def apply_styles(self):
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,70);
                border-radius: 14px;
                padding: 8px;
                color: black;
                font-size: 14px;
            }

            QPushButton {
                background-color: rgba(0,170,255,200);
                color: black;
                padding: 10px;
                border-radius: 12px;
                font-weight: 800;
            }

            QPushButton:hover {
                background-color: rgba(0,200,255,230);
            }

            QProgressBar {
                background: rgba(255,255,255,60);
                border-radius: 14px;
                height: 18px;
                text-align: center;
            }

            QProgressBar::chunk {
                border-radius: 14px;
                background-color: #00D4FF;
            }
        """)

    # ---------------- File dialogs ---------------- #

    def browse_input(self):
        file_path,_ = QFileDialog.getOpenFileName(
            self,
            "Select Audio/Video File",
            "",
            "Media Files (*.mp3 *.wav *.mp4 *.m4a *.flv *.aac);;All Files (*)"
        )
        if file_path:
            self.input_edit.setText(file_path)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self,"Select Output Folder")
        if folder:
            self.output_edit.setText(folder)

    def open_output(self):
        path = self.output_edit.text()
        if not os.path.isdir(path):
            return

        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open",path])
        else:
            subprocess.run(["xdg-open",path])

    # ---------------- Processing ---------------- #

    def start_processing(self):

        input_path = self.input_edit.text().strip()
        output_path = self.output_edit.text().strip()

        if not os.path.isfile(input_path):
            QMessageBox.critical(self,"Error","Invalid input file")
            return

        if not os.path.isdir(output_path):
            QMessageBox.critical(self,"Error","Invalid output folder")
            return

        self.progress_bar.setRange(0,0)
        self.status.setText("Processing...")
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.input_edit.setEnabled(False)
        self.output_edit.setEnabled(False)
        self.input_btn.setEnabled(False)
        self.browse_out.setEnabled(False)
        self.open_btn.setEnabled(False)

        self.worker = Worker(input_path,output_path)
        self.worker.finished.connect(self.processing_finished)
        self.worker.error.connect(self.processing_error)
        self.worker.start()

    def cancel_processing(self):
        if hasattr(self,"worker") and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait()
            self.status.setText("Cancelled")
            self.reset_ui()

    def processing_finished(self,result):
        self.progress_bar.setRange(0,100)
        self.progress_bar.setValue(100)
        self.status.setText("Done")
        QMessageBox.information(self,"Success",f"Saved:\n{result}")
        self.reset_ui()

    def processing_error(self,message):
        self.status.setText("Error")
        QMessageBox.critical(self,"Error",message)
        self.reset_ui()

    def reset_ui(self):
        self.progress_bar.setRange(0,100)
        self.progress_bar.setValue(0)

        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        self.input_edit.setEnabled(True)
        self.output_edit.setEnabled(True)
        self.input_btn.setEnabled(True)
        self.browse_out.setEnabled(True)
        self.open_btn.setEnabled(True)

    def closeEvent(self,event):
        if hasattr(self,"worker") and self.worker.isRunning():
            self.worker.cancel()
            self.worker.quit()
            self.worker.wait()
        event.accept()


# ---------------- Run ---------------- #

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.join(BASE_DIR,"icon.jpg")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())