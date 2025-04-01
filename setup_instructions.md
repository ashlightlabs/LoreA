
# Lore Assistant MVP – Setup Guide

This guide walks you through setting up and running the Lore Assistant MVP in a virtual environment.

---

## 1. Clone or unzip the project

```bash
cd lore_assistant_mvp
```

## 2. Create and activate a virtual environment

### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

If needed:
```bash
pip install fastapi uvicorn openai streamlit faiss-cpu numpy python-dotenv
pip freeze > requirements.txt
```

## 4. Set up your OpenAI API Key

Create a file named `.env` in the root of your project:

```
OPENAI_API_KEY=your-openai-api-key-here
```

## 5. Run the Streamlit app

```bash
streamlit run frontend/app.py
```

---

## Notes

- Your lore entries will be saved in `data/lore.db`
- You can export results from the UI as JSON or Markdown in future versions
