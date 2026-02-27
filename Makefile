.PHONY: dev prod seed test test-unit test-api test-e2e migrate backup qr-test logs down

PYTHON = .venv/bin/python
PYTEST = .venv/bin/python -m pytest

# ─── Development ─────────────────────────────────────────────────────────────

dev:
	docker-compose -f docker-compose.dev.yml up --build

prod:
	docker-compose up --build -d

down:
	docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	docker-compose down 2>/dev/null || true

logs:
	docker-compose logs -f

# ─── Database ─────────────────────────────────────────────────────────────────

migrate:
	$(PYTHON) -m alembic upgrade head

seed:
	mkdir -p data
	$(PYTHON) seed.py

# ─── Testing ──────────────────────────────────────────────────────────────────

test:
	$(PYTEST) tests/ -v

test-unit:
	$(PYTEST) tests/test_models.py -v

test-api:
	$(PYTEST) tests/test_api/ -v

test-e2e:
	$(PYTEST) tests/test_e2e/ -v

# ─── Utilities ────────────────────────────────────────────────────────────────

backup:
	mkdir -p backups
	cp data/inventory.db backups/inventory_$$(date +%Y%m%d_%H%M%S).db
	@echo "Záloha uložena do backups/"

qr-test:
	$(PYTHON) -c "import sys; sys.path.insert(0, '.'); from app.database import SessionLocal, Base, engine; import app.models; Base.metadata.create_all(bind=engine); from app.services.qr_service import generate_batch_pdf; from sqlalchemy import select; from app.models.item import Item; db = SessionLocal(); items = db.scalars(select(Item)).all(); pdf = generate_batch_pdf(db, [i.id for i in items[:4]]) if items else None; [open('/tmp/test-qr-labels.pdf','wb').write(pdf), print('PDF uloženo do /tmp/test-qr-labels.pdf')] if pdf else print('Nejdřív spusť make seed'); db.close()"

# ─── Setup ────────────────────────────────────────────────────────────────────

setup:
	test -d .venv || python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	mkdir -p data
	cp -n .env.example .env 2>/dev/null || true
	$(PYTHON) -m alembic upgrade head

run:
	$(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
