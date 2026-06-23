.PHONY: setup backend frontend

setup:
	python3 -m venv backend/.venv
	. backend/.venv/bin/activate && pip install -r backend/requirements.txt
	cd frontend && npm install

backend:
	. backend/.venv/bin/activate && cd backend && uvicorn main:app --reload --port 8011

frontend:
	cd frontend && npm run dev
