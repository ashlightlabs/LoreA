
setup:
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt

run:
	source venv/bin/activate && streamlit run frontend/app.py

freeze:
	source venv/bin/activate && pip freeze > requirements.txt
