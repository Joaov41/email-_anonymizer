The Email Processor and Redactor is a Python application designed to process .eml files, identify sensitive entities using natural language processing, and manually redacting parts of the emails, as well as deanonymize information efficiently. 
It includes an GUI and integrates SpaCy for entity recognition and customization.
Uses GPT4-o mini to summarize and engage in Q&A with the LLM about the redacted emails.

Features:
Drag-and-Drop Email Processing: Drop .eml files directly into the app for extraction and processing.

![CleanShot 2024-11-19 at 17 48 59@2x](https://github.com/user-attachments/assets/f794f4c8-1bd1-472f-849e-af73c72af72f)



Entity Recognition: Identify automatically some entities such as people, locations, and organizations.


![CleanShot 2024-11-19 at 17 52 37@2x](https://github.com/user-attachments/assets/91bc7ca5-98a1-41dd-ac07-10f4d7a9ac8c)



Customizable Redaction: manually redact sensitive information by selecting text 

![CleanShot 2024-11-19 at 17 56 03@2x](https://github.com/user-attachments/assets/0bb0808b-d94c-43a8-8f96-e1255ef9e5c0)

![CleanShot 2024-11-19 at 17 57 10@2x](https://github.com/user-attachments/assets/07551bdd-b853-4898-8425-345f8ac63a86)

Redacted works or entire sentences will be added to a database, so that if those expressions show up on a a different email, they will show as automatically redacted. 

Summary provided by the LLM, as well as engage in Q&A about the emails. All the content sent to the LLM is redacted. 
Multilingual Support: Supports English and Portuguese text processing so far.
Deanonymization: Restore redacted entities when needed using a redaction database.
If an email is heavily redacted, it can be difficult to understand the output from the LLM with so much redacted.
In that case, just paste the output in the Deanonymizer parte and it will show the content cleaned, which the LLM never had acess to.   

	
Prerequisites: Python 3.8 or later

Download the project folder
//CD into the project folder
// pip install -r requirements.txt  

Download the spacy models:

python -m spacy download en_core_web_md

python -m spacy download pt_core_news_md ( do not download if use in PT is not intended) 

Add open ai key on the app.py file

python app.py  

