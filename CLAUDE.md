# Inventarizační systém — CLAUDE.md

Tento soubor je primární reference pro všechny agenty a session pracující na tomto projektu.
Přečti ho celý před jakoukoliv akcí.

---

## Projekt

**Název:** AssetTrack — interní inventarizační systém  
**Účel:** Správa firemního majetku pomocí QR kódů a mobilního telefonu jako skeneru  
**Jazyk UI:** Čeština  
**Stav:** Vývoj od nuly

---

## Architektura

```
/app
  /models        → SQLAlchemy ORM modely
  /routers       → FastAPI routery (jeden soubor = jeden resource)
  /services      → business logika (žádná logika v routerech)
  /schemas       → Pydantic modely pro request/response
  /templates     → Jinja2 HTML šablony
  /static        → CSS, JS (jen vlastní, zbytek CDN)
/alembic         → DB migrace
/tests           → pytest testy (mirror struktura /app)
/nginx           → nginx.conf
Dockerfile
docker-compose.yml
docker-compose.dev.yml
Makefile
.env.example
seed.py
```

---

## Technický stack — NEMĚNIT bez konzultace

| Vrstva | Technologie | Verze |
|--------|-------------|-------|
| Backend | FastAPI | latest stable |
| ORM | SQLAlchemy | 2.x |
| Migrace | Alembic | latest |
| DB dev | SQLite | built-in |
| DB prod | MariaDB | 10.11 |
| Templates | Jinja2 | přes FastAPI |
| Frontend | HTMX + Bootstrap 5 | CDN |
| QR gen | qrcode + pillow | latest |
| PDF | reportlab | latest |
| Excel | openpyxl | latest |
| Testy | pytest + httpx + playwright | latest |
| Kontejner | Docker + docker-compose | latest |

**Zakázáno přidat:** React, Vue, Angular, npm build kroky, OAuth, Redis, Celery

---

## Datový model

### Pravidla — KRITICKÉ

1. `assignments` tabulka je **VŽDY append-only** — žádný UPDATE, žádný DELETE
2. Aktuální lokace položky = poslední záznam v `assignments` pro daný `item_id`
3. Soft delete přes `is_active = False` — nikdy fyzické mazání položek
4. Každý model má `created_at` a `updated_at` (auto)
5. Audit scan je **idempotentní** — stejná položka naskenovaná 2× v rámci auditu = jeden záznam

### Schéma

```sql
users (id, username, email, hashed_password, role, is_active, created_at, updated_at)

locations (id, name, code, building, floor, description, is_active, created_at, updated_at)

items (id, code, name, category, description, serial_number, purchase_date, 
       purchase_price, photo_url, is_active, created_at, updated_at)

assignments (id, item_id→items, location_id→locations, user_id→users, 
             note, assigned_at)   ← NO updated_at, append-only

audits (id, name, started_at, closed_at, created_by→users, status[open/closed])

audit_scans (id, audit_id→audits, item_id→items, location_id→locations,
             scanned_by→users, scanned_at)   ← unique(audit_id, item_id)
```

---

## API konvence

- Všechny endpointy vrací JSON dle Pydantic schématu
- Chyby: `{"detail": "popis chyby", "code": "ERROR_CODE"}`
- Stránkování: `?page=1&size=50` → `{"items": [...], "total": N, "page": 1, "pages": N}`
- Datum vždy ISO 8601 UTC
- Endpoint `/health` musí vždy existovat a vracet `{"status": "ok"}`

### Routery

```
GET/POST        /api/items
GET/PUT/DELETE  /api/items/{id}
GET             /api/items/{id}/history
GET             /api/items/{id}/qr

GET/POST        /api/locations
GET/PUT/DELETE  /api/locations/{id}
GET             /api/locations/{id}/items

POST            /api/moves              body: {item_id, location_id, note?}

GET/POST        /api/audits
GET             /api/audits/{id}
POST            /api/audits/{id}/scan   body: {item_id}
POST            /api/audits/{id}/close
GET             /api/audits/{id}/report

GET             /api/qr/item/{id}       → PNG
GET             /api/qr/location/{id}   → PNG
GET             /api/qr/batch           ?ids=1,2,3 → PDF

GET             /api/export/excel
GET             /api/export/pdf/{audit_id}

GET             /health
```

### Scan URL formát

QR kód musí odkazovat na: `{BASE_URL}/scan/{item_code}`  
Tato URL přesměruje na detail položky nebo přímo do aktivní inventury.

---

## Frontend konvence

- **Mobile-first** — nejdřív design pro 375px, pak desktop
- Buttony min. `44px` výška (touch target)
- HTMX partial updates pro: live search, progress bar inventury, scan feedback
- Každá stránka musí fungovat i bez JavaScriptu (graceful degradation)
- Flash zprávy přes session (success/error/info)
- Navbar: Dashboard | Majetek | Lokace | Inventury | Tisk | Admin

### CDN závislosti (pevné verze)

```html
Bootstrap 5.3: https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/...
HTMX 1.9: https://unpkg.com/htmx.org@1.9.0/dist/htmx.min.js
html5-qrcode: https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js
```

---

## Docker & prostředí

### ENV proměnné (všechny musí být v .env.example)

```env
APP_ENV=development          # development / production
BASE_URL=http://localhost:8000
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///./data/inventory.db
# Prod:
# DATABASE_URL=mysql+pymysql://user:pass@mariadb/inventory
FIRST_ADMIN_USER=admin
FIRST_ADMIN_PASS=admin123
```

### Docker pravidla

- Multi-stage Dockerfile (builder + runtime)
- Alpine base image
- Non-root user v kontejneru
- Health check na `/health`
- Volumes: `./data` pro DB a uploaded soubory
- `restart: unless-stopped` v compose

---

## Testování

### Pokrytí — minimum

- Každý SQLAlchemy model: unit test pro create/read
- Každý API endpoint: integration test přes httpx TestClient
- Scan endpoint: test idempotence (2× scan = 1 záznam)
- Přesun: test že assignment je append-only
- Export: test že PDF a Excel se vygenerují bez chyby
- Docker: `docker-compose up --build` + `GET /health` = 200

### Spuštění testů

```bash
make test          # všechny testy
make test-unit     # jen unit
make test-api      # jen API
make test-e2e      # playwright
```

---

## Makefile příkazy

```bash
make dev        # spustí docker-compose.dev.yml s hot-reload
make prod       # spustí produkční stack
make seed       # naplní DB testovacími daty
make test       # spustí všechny testy
make migrate    # spustí alembic upgrade head
make backup     # záloha DB do ./backups/
make qr-test    # vygeneruje testovací PDF se štítky
make logs       # docker-compose logs -f
make down       # zastaví všechny kontejnery
```

---

## Agenti a jejich zodpovědnosti

Projekt se buildí pomocí 5 specializovaných agentů v tomto pořadí:

```
[Agent 1: DB]  →  [Agent 2: API]  →  [Agent 3: Frontend] ↘
                                   →  [Agent 4: QR/Export] → [Agent 5: Docker]
```

Každý agent před zahájením práce:
1. Přečte tento CLAUDE.md
2. Zkontroluje existující soubory ve své oblasti
3. Spustí stávající testy aby viděl co funguje
4. Pracuje, pak spustí testy znovu

**Agent nesmí měnit kód mimo svou zodpovědnost** bez explicitního pokynu.

---

## Časté chyby — VYHNI SE

- ❌ Updatovat `assignments` záznamy — vždy jen INSERT
- ❌ Přidat npm/yarn/webpack závislost
- ❌ Hard-kódovat BASE_URL nebo SECRET_KEY
- ❌ Mazat položky z DB (použij `is_active = False`)
- ❌ Logika v Jinja2 templates (patří do services)
- ❌ Přímé SQL dotazy mimo SQLAlchemy (kromě seed.py)
- ❌ Committovat `.env` soubor

---

## Definition of Done

Projekt je hotový když:

- [ ] `make dev` nastartuje bez chyb
- [ ] `make prod` nastartuje bez chyb  
- [ ] `GET /health` vrátí 200
- [ ] Lze přidat položku, přiřadit lokaci, přesunout
- [ ] QR kód naskenovaný telefonem otevře správnou URL
- [ ] Inventura: vytvoření → skenování → report funguje end-to-end
- [ ] PDF se štítky jde vytisknout
- [ ] Excel export obsahuje historii přesunů
- [ ] `make test` projde bez chyb
- [ ] Všechny ENV jsou v `.env.example`
