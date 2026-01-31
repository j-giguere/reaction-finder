.PHONY: install run clean

ENV_NAME = reaction-finder

install:
	conda create -n $(ENV_NAME) python=3.11 -y
	conda run -n $(ENV_NAME) pip install -r requirements.txt

run:
	conda run -n $(ENV_NAME) python app.py

clean:
	conda remove -n $(ENV_NAME) --all -y 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
