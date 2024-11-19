import sys
import os
import re
import uuid
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QLabel,
    QVBoxLayout, QWidget, QMenu, QTextEdit, QDialog, QCheckBox,
    QDialogButtonBox, QScrollArea, QScrollBar, QTabWidget, QPushButton,
    QHBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QTextCursor
from utils import find_entities
from redactor import RedactionDatabase, clean_text, redact_text, apply_redaction, unredact_text
from email import policy
from email.parser import BytesParser

class RedactingTextEdit(QTextEdit):
    text_selected = pyqtSignal(str, bool)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.selection_start = None
        self.is_selecting = False
        self.redaction_db = RedactionDatabase()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.selection_start = event.pos()
            self.is_selecting = False
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selection_start is not None:
            if not self.is_selecting and (event.pos() - self.selection_start).manhattanLength() > QApplication.startDragDistance():
                self.is_selecting = True
            
            if self.is_selecting:
                cursor = self.textCursor()
                cursor.setPosition(self.cursorForPosition(self.selection_start).position())
                cursor.setPosition(self.cursorForPosition(event.pos()).position(), QTextCursor.MoveMode.KeepAnchor)
                self.setTextCursor(cursor)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.selection_start is not None and self.is_selecting:
            cursor = self.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                if selected_text:
                    self.text_selected.emit(selected_text, True)
            self.selection_start = None
            self.is_selecting = False
        else:
            super().mouseReleaseEvent(event)
            cursor = self.textCursor()
            if cursor.hasSelection():
                selected_text = cursor.selectedText().strip()
                if selected_text:
                    self.text_selected.emit(selected_text, False)

    def show_context_menu(self, position):
        context_menu = self.createStandardContextMenu()

        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        context_menu.addAction(undo_action)

        copy_action = QAction("Copy to Clipboard", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.copy)
        context_menu.addAction(copy_action)

        delete_all_action = QAction("Delete All Instances", self)
        delete_all_action.triggered.connect(self.delete_all_selected_text)
        context_menu.addAction(delete_all_action)

        context_menu.exec(self.mapToGlobal(position))

    def delete_all_selected_text(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            if selected_text:
                self.main_window.delete_all_instances(selected_text)

    def redact_selected_text(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            tag = self.redaction_db.get_tag(selected_text)
            if not tag:
                tag = f"<ANON_{uuid.uuid4().hex[:8]}>"
                self.redaction_db.add_redaction(selected_text, tag)
            cursor.insertText(tag)

    def __del__(self):
        self.redaction_db.close()

class EntitySelectionDialog(QDialog):
    def __init__(self, entities, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Entities to Redact")

        layout = QVBoxLayout(self)

        instructions = QLabel("Select the entities you wish to redact:")
        layout.addWidget(instructions)

        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        self.checkboxes = []
        for entity_type, entity_set in entities.items():
            for entity in sorted(entity_set):
                checkbox = QCheckBox(f"{entity} ({entity_type})")
                checkbox.entity = entity
                checkbox.entity_type = entity_type
                checkbox.setChecked(False)
                self.checkboxes.append(checkbox)
                scroll_layout.addWidget(checkbox)

        scroll_widget.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_entities(self):
        selected = set()
        for checkbox in self.checkboxes:
            if checkbox.isChecked():
                selected.add((checkbox.entity_type, checkbox.entity))
        return selected

class EmailProcessor:
    def __init__(self, language='en'):
        self.language = language
        self.cleaned_text = ''

    def find_entities_in_text(self, text):
        return find_entities(text, self.language)

    def process_eml_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)
        except Exception as e:
            raise RuntimeError(f"Failed to parse {file_path}: {e}")

        text_content = []
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type in ('text/plain', 'text/html') and not part.is_multipart():
                try:
                    charset = part.get_content_charset()
                    charset = charset if charset else 'utf-8'
                    part_text = part.get_payload(decode=True).decode(charset, errors='replace')
                    text_content.append(part_text)
                except Exception as e:
                    print(f"Failed to decode part of {file_path}: {e}")
                    continue

        combined_text = '\n'.join(text_content)
        self.cleaned_text = clean_text(combined_text)
        entities = self.find_entities_in_text(self.cleaned_text)

        return self.cleaned_text, entities

class NoSwitchTabWidget(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabBar().setAcceptDrops(False)
        self.setMovable(False)
        self.setTabBarAutoHide(True)

    def mousePressEvent(self, event):
        # Prevent tab switching on mouse press
        if self.tabBar().tabAt(event.pos()) != self.currentIndex():
            event.ignore()
        else:
            super().mousePressEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Email Processor and Redactor")
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)

        self.language = 'en'
        self.processor = EmailProcessor(self.language)
        self.redaction_db = RedactionDatabase()

        self.tab_widget = NoSwitchTabWidget(self)
        self.setCentralWidget(self.tab_widget)

        # Anonymizer tab
        anonymizer_widget = QWidget()
        anonymizer_layout = QVBoxLayout(anonymizer_widget)
        
        # Add button layout at the top
        button_layout = QHBoxLayout()
        self.new_email_button = QPushButton("New Email")
        self.new_email_button.clicked.connect(self.reset_application_state)
        button_layout.addWidget(self.new_email_button)
        button_layout.addStretch()  # This pushes the button to the left
        anonymizer_layout.addLayout(button_layout)
        
        self.label = QLabel("Drag and drop an .eml file here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        anonymizer_layout.addWidget(self.label)
        self.text_edit = RedactingTextEdit(self, self)
        self.text_edit.setVisible(False)
        anonymizer_layout.addWidget(self.text_edit)
        self.tab_widget.addTab(anonymizer_widget, "Anonymizer")

        # Deanonymizer tab
        deanonymizer_widget = QWidget()
        deanonymizer_layout = QVBoxLayout(deanonymizer_widget)
        self.deanonymizer_input = QTextEdit()
        self.deanonymizer_output = QTextEdit()
        self.deanonymize_button = QPushButton("Deanonymize")
        deanonymizer_layout.addWidget(QLabel("Input:"))
        deanonymizer_layout.addWidget(self.deanonymizer_input)
        deanonymizer_layout.addWidget(self.deanonymize_button)
        deanonymizer_layout.addWidget(QLabel("Output:"))
        deanonymizer_layout.addWidget(self.deanonymizer_output)
        self.tab_widget.addTab(deanonymizer_widget, "Deanonymizer")

        # Connect the deanonymize button to the deanonymize method
        self.deanonymize_button.clicked.connect(self.deanonymize_text)

        self.text_edit.text_selected.connect(self.handle_text_selection)

        menubar = self.menuBar()
        language_menu = menubar.addMenu("Language")
        save_menu = menubar.addMenu("Save")

        en_action = QAction("English", self)
        pt_action = QAction("Portuguese", self)
        language_menu.addAction(en_action)
        language_menu.addAction(pt_action)
        en_action.triggered.connect(lambda: self.set_language('en'))
        pt_action.triggered.connect(lambda: self.set_language('pt'))

        save_action = QAction("Save Redacted Text", self)
        save_menu.addAction(save_action)
        save_action.triggered.connect(self.save_redacted_text)

        self.current_file_path = None

    def reset_application_state(self):
        """Reset the application to its initial state"""
        self.current_file_path = None
        self.text_edit.setVisible(False)
        self.text_edit.clear()
        self.label.setVisible(True)
        self.tab_widget.setCurrentIndex(0)  # Switch to Anonymizer tab

    def set_language(self, lang):
        self.language = lang
        self.processor = EmailProcessor(self.language)
        QMessageBox.information(self, "Language Changed", f"Language set to {'English' if lang == 'en' else 'Portuguese'}.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().endswith('.eml'):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        self.tab_widget.setCurrentIndex(0)  # Ensure Anonymizer tab is active
        urls = event.mimeData().urls()
        if len(urls) != 1:
            QMessageBox.warning(self, "Multiple Files", "Please drop only one .eml file at a time.")
            return
        file_path = urls[0].toLocalFile()
        if not file_path.endswith('.eml'):
            QMessageBox.warning(self, "Invalid File", "Please drop a valid .eml file.")
            return
        self.process_file(file_path)

    def process_file(self, file_path):
        try:
            cleaned_text, entities = self.processor.process_eml_file(file_path)
            self.current_file_path = file_path

            dialog = EntitySelectionDialog(entities, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_entities = dialog.get_selected_entities()
                entities_to_redact = {}
                for entity_type, entity in selected_entities:
                    if entity_type not in entities_to_redact:
                        entities_to_redact[entity_type] = set()
                    entities_to_redact[entity_type].add(entity)
                
                redacted_text, redaction_map = redact_text(cleaned_text, entities_to_redact)
                
                auto_redacted_text = self.apply_automatic_redaction(redacted_text)
                
                self.display_text(auto_redacted_text, entities)
            else:
                auto_redacted_text = self.apply_automatic_redaction(cleaned_text)
                self.display_text(auto_redacted_text, entities)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while processing the file:\n{str(e)}")

    def apply_automatic_redaction(self, text):
        redacted_items = self.redaction_db.get_all_redacted_items()
        for item in redacted_items:
            tag = self.redaction_db.get_tag(item)
            if tag:
                text = re.sub(re.escape(item), tag, text, flags=re.IGNORECASE)
        return text

    def display_text(self, text, entities):
        self.label.setVisible(False)
        self.text_edit.setVisible(True)
        self.text_edit.setPlainText(text)

    def handle_text_selection(self, selected_text, shift_pressed):
        if shift_pressed:
            self.delete_all_instances(selected_text)
        else:
            self.redact_all_instances(selected_text)

    def redact_all_instances(self, text_to_redact):
        if not text_to_redact:
            return

        cursor = self.text_edit.textCursor()
        scroll_value = self.text_edit.verticalScrollBar().value()

        text_to_redact = '\n'.join(text_to_redact.splitlines())
        document_text = '\n'.join(self.text_edit.toPlainText().splitlines())
        
        escaped_text = re.escape(text_to_redact).replace(r'\n', r'\s*\n\s*')
        pattern = re.compile(escaped_text, re.DOTALL | re.MULTILINE)

        tag = self.redaction_db.get_tag(text_to_redact)
        if not tag:
            tag = f"<ANON_{uuid.uuid4().hex[:8]}>"
            self.redaction_db.add_redaction(text_to_redact, tag)

        redacted_text, count = pattern.subn(tag, document_text)

        if count == 0:
            QMessageBox.information(self, "No Matches", f"No instances of the selected text were found to redact.")
            return

        self.text_edit.setPlainText(redacted_text)

        cursor.setPosition(min(cursor.position(), len(redacted_text)))
        self.text_edit.setTextCursor(cursor)
        self.text_edit.verticalScrollBar().setValue(scroll_value)

        QMessageBox.information(self, "Redacted", f"All {count} instance(s) of the selected text have been redacted.")

    def delete_all_instances(self, text_to_delete):
        if not text_to_delete:
            return

        cursor = self.text_edit.textCursor()
        scroll_value = self.text_edit.verticalScrollBar().value()

        text_to_delete = '\n'.join(text_to_delete.splitlines())
        document_text = '\n'.join(self.text_edit.toPlainText().splitlines())
        
        escaped_text = re.escape(text_to_delete).replace(r'\n', r'\s*\n\s*')
        
        pattern = re.compile(escaped_text, re.DOTALL | re.MULTILINE)

        deleted_text, count = pattern.subn('', document_text)

        if count == 0:
            QMessageBox.information(self, "No Matches", f"No instances of the selected text were found to delete.")
            return

        self.text_edit.setPlainText(deleted_text)

        cursor.setPosition(min(cursor.position(), len(deleted_text)))
        self.text_edit.setTextCursor(cursor)
        self.text_edit.verticalScrollBar().setValue(scroll_value)

        QMessageBox.information(self, "Deleted", f"All {count} instance(s) of the selected text have been deleted.")

    def save_redacted_text(self):
        if not self.text_edit.isVisible():
            QMessageBox.warning(self, "No Text", "There is no text to save. Please process an .eml file first.")
            return

        if self.current_file_path:
            default_save_path = os.path.splitext(self.current_file_path)[0] + "_redacted.txt"
        else:
            default_save_path = "redacted_text.txt"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Redacted Text",
            default_save_path,
            "Text Files (*.txt)"
        )
        if save_path:
            try:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(self.text_edit.toPlainText())
                QMessageBox.information(self, "Success", f"Redacted text saved to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file:\n{str(e)}")

    def deanonymize_text(self):
        anonymized_text = self.deanonymizer_input.toPlainText()
        deanonymized_text = self.perform_deanonymization(anonymized_text)
        self.deanonymizer_output.setPlainText(deanonymized_text)

    def perform_deanonymization(self, text):
        # Find all <ANON_*> tags in the text
        anon_tags = re.findall(r'<ANON_[a-f0-9]{8}>', text)
        
        for tag in anon_tags:
            # Look up the original text in the database
            original = self.redaction_db.get_original(tag)
            if original:
                # Replace the tag with the original text
                text = text.replace(tag, original)
        
        return text

    def closeEvent(self, event):
        self.redaction_db.close()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
