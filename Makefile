
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

install:
	pip install -r requirements.txt