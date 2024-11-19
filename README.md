The Email Processor and Redactor is a Python application designed to process .eml files, identify sensitive entities using natural language processing, and manually redacting parts of the emails, as well as deanonymize information efficiently. 
It includes an GUI and integrates SpaCy for entity recognition and customization.
Uses GPT4-o mini to summarize and engage in Q&A with the LLM about the redacted emails.

Features:
Drag-and-Drop Email Processing: Drop .eml files directly into the app for extraction and processing.
Entity Recognition: Identify automatically some entities such as people, locations, and organizations.
Customizable Redaction: manually redact sensitive information by selecting text
SUmmary provided by the LLM, as well as engage in Q&A about the emails.
Multilingual Support: Supports English and Portuguese text processing so far.
Deanonymization: Restore redacted entities when needed using a redaction database.

	
Prerequisites: Python 3.8 or later

Download the project folder
//CD into the project folder
// pip install -r requirements.txt  

Download the spacy models:

python -m spacy download en_core_web_md

python -m spacy download pt_core_news_md ( do not download if use in PT is not intended) 

python app.py  

