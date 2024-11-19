# redactor.py
import re
import uuid
import sqlite3

class RedactionDatabase:
    def __init__(self):
        self.conn = sqlite3.connect('redactions.db')
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS redactions
            (original TEXT PRIMARY KEY, tag TEXT)
        ''')
        self.conn.commit()

    def add_redaction(self, original, tag):
        self.cursor.execute('INSERT OR REPLACE INTO redactions (original, tag) VALUES (?, ?)', (original, tag))
        self.conn.commit()

    def get_tag(self, original):
        self.cursor.execute('SELECT tag FROM redactions WHERE original = ?', (original,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_original(self, tag):
        self.cursor.execute('SELECT original FROM redactions WHERE tag = ?', (tag,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_all_redacted_items(self):
        self.cursor.execute('SELECT original FROM redactions')
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        self.conn.close()

def clean_text(text):
    # Remove any HTML tags
    text = re.sub('<[^<]+?>', '', text)
    # Replace multiple newlines with a single newline
    text = re.sub(r'\n\s*\n', '\n', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

def redact_text(text, entities):
    redacted_text = text
    redaction_map = {}
    redaction_db = RedactionDatabase()

    for entity_type, entity_set in entities.items():
        for entity in entity_set:
            if entity not in redaction_map:
                tag = redaction_db.get_tag(entity)
                if not tag:
                    tag = f"<ANON_{uuid.uuid4().hex[:8]}>"
                    redaction_db.add_redaction(entity, tag)
                redaction_map[entity] = tag
            else:
                tag = redaction_map[entity]

            # Use word boundaries to avoid partial word matches
            pattern = r'\b' + re.escape(entity) + r'\b'
            redacted_text = re.sub(pattern, tag, redacted_text, flags=re.IGNORECASE)

    redaction_db.close()
    return redacted_text, redaction_map

def apply_redaction(text, redaction_map):
    """
    Apply redaction to the text using the provided redaction map.
    """
    redacted_text = text
    redaction_db = RedactionDatabase()
    for original, tag in redaction_map.items():
        redaction_db.add_redaction(original, tag)
        pattern = r'\b' + re.escape(original) + r'\b'
        redacted_text = re.sub(pattern, tag, redacted_text, flags=re.IGNORECASE)
    redaction_db.close()
    return redacted_text

def unredact_text(redacted_text, redaction_map):
    """
    Reverse the redaction process using the redaction map.
    """
    unredacted_text = redacted_text
    for original, tag in redaction_map.items():
        unredacted_text = unredacted_text.replace(tag, original)
    return unredacted_text