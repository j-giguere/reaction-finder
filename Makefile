.PHONY: install run clean ollama-check ollama-pull

ENV_NAME = reaction-finder
OLLAMA_MODEL ?= llama3.2

install:
	conda create -n $(ENV_NAME) python=3.11 -y
	conda run -n $(ENV_NAME) pip install -r requirements.txt

run:
	conda run -n $(ENV_NAME) python app.py

clean:
	conda remove -n $(ENV_NAME) --all -y 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Ollama commands
ollama-check:
	@echo "Checking Ollama status..."
	@ollama --version || (echo "Error: Ollama is not installed. Visit https://ollama.ai to install." && exit 1)
	@curl -s http://localhost:11434/api/tags > /dev/null && echo "Ollama server is running" || echo "Warning: Ollama server is not running. Start it with 'ollama serve'"

ollama-pull:
	@echo "Pulling $(OLLAMA_MODEL) model..."
	ollama pull $(OLLAMA_MODEL)
