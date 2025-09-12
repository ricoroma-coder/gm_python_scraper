#!/bin/bash
cd /home/scraper
source .venv/bin/activate
python3 scrapper_google_business.py "$@"
