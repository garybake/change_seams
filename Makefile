run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

migrate:
	alembic upgrade head