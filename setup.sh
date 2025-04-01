#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Don't forget to add your OPENAI_API_KEY to .env"
