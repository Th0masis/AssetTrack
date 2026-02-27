# AssetTrack — Interní inventarizační systém

Webová aplikace pro správu firemního majetku pomocí QR kódů a mobilního telefonu jako skeneru.

## Co to je

AssetTrack umožňuje:
- **Evidovat majetek** — notebooky, monitory, nábytek, telefony, vše s kódem a kategorií
- **Sledovat polohu** — každá položka má historii přesunů mezi lokacemi
- **Inventury** — mobilním telefonem naskenujete QR kód a inventura zaznamená polohu
- **Tisknout štítky** — PDF s QR kódy pro lepení na fyzický majetek
- **Exportovat data** — Excel s historií přesunů, PDF zprávy z inventur

## Technický stack

| Vrstva | Technologie |
|--------|-------------|
| Backend | FastAPI (latest) |
| ORM | SQLAlchemy 2.x |
| Migrace | Alembic |
| DB dev | SQLite (built-in) |
| DB prod | MariaDB 10.11 |
| Templates | Jinja2 |
| Frontend | HTMX 1.9 (lokálně) + vlastní CSS (bez Bootstrap/CDN) |
| QR gen | qrcode + pillow |
| PDF | reportlab + DejaVu font |
| Excel | openpyxl |
| Testy | pytest + httpx |
| Kontejner | Docker multi-stage Alpine |

## Instalace (lokálně bez Dockeru)

```bash
# 1. Klonovat repozitář
git clone <repo> assettrack && cd assettrack

# 2. Virtuální prostředí
python3 -m venv .venv && source .venv/bin/activate

# 3. Závislosti
pip install -r requirements.txt

# 4. Konfigurace
cp .env.example .env
# Upravte .env dle potřeby

# 5. Databáze
mkdir -p data
alembic upgrade head

# 6. Testovací data (volitelné)
python seed.py

# 7. Spustit
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Otevřít v prohlížeči: http://localhost:8000

## Instalace přes Docker

```bash
# Dev mode s hot-reload
make dev

# Produkční stack
make prod

# Testovací data
make seed

# Zastavit
make down
```

## Makefile příkazy

| Příkaz | Popis |
|--------|-------|
| `make dev` | Dev server s hot-reload |
| `make prod` | Produkční stack |
| `make down` | Zastavit kontejnery |
| `make seed` | Naplnit DB testovacími daty |
| `make test` | Všechny testy |
| `make test-unit` | Jen unit testy modelů |
| `make test-api` | Jen API testy |
| `make migrate` | Spustit Alembic migrace |
| `make backup` | Záloha databáze |
| `make qr-test` | Generovat testovací PDF štítky |
| `make logs` | Docker logy |

## Uživatelské role

| Role | Oprávnění |
|------|-----------|
| `admin` | Vše včetně správy uživatelů (`/admin/uzivatele`) |
| `spravce` | Přidat/upravit/vyřadit majetek, lokace, inventury, import |
| `user` | Pouze čtení a skenování QR kódů |

První admin účet se vytvoří automaticky při startu dle `FIRST_ADMIN_USER` a `FIRST_ADMIN_PASS` v `.env`.

## Mobilní zařízení

Mobilní layout je optimalizován pro **skenování**:
- Spodní navigace: Dashboard, Majetek, Skenovat, Inventury, Lokace
- Editační akce (Upravit, Přesunout, Vyřadit, Uzavřít inventuru) jsou na mobilu skryté
- Přihlášený uživatel vidí svůj avatar a tlačítko odhlášení v horní liště

## Databáze

### SQLite (výchozí pro vývoj)

```env
DATABASE_URL=sqlite:///./data/inventory.db
```

### MariaDB (produkce)

#### 1. Příprava databáze

```sql
CREATE DATABASE assettrack CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'assettrack'@'%' IDENTIFIED BY 'silne-heslo';
GRANT ALL PRIVILEGES ON assettrack.* TO 'assettrack'@'%';
FLUSH PRIVILEGES;
```

#### 2. Konfigurace `.env`

```env
DATABASE_URL=mysql+pymysql://assettrack:silne-heslo@localhost/assettrack
```

#### 3. Migrace

```bash
alembic upgrade head
```

#### 4. Docker Compose s MariaDB

```bash
docker-compose --profile mariadb up -d
```

`docker-compose.yml` obsahuje profil `mariadb` se službou MariaDB 10.11. Při jeho použití se `DATABASE_URL` v `.env` musí odkazovat na hostname `mariadb`:

```env
DATABASE_URL=mysql+pymysql://assettrack:heslo@mariadb/assettrack
```

## API dokumentace

Po spuštění dostupná na: http://localhost:8000/docs

### Hlavní endpointy

| Metoda | URL | Popis |
|--------|-----|-------|
| GET | `/health` | Health check |
| GET/POST | `/api/items` | Seznam / přidat majetek |
| GET/PUT/DELETE | `/api/items/{id}` | Detail / upravit / smazat |
| POST | `/api/items/{id}/dispose` | Vyřadit položku |
| GET | `/api/items/{id}/history` | Historie přesunů |
| GET/POST | `/api/locations` | Lokace |
| PUT/DELETE | `/api/locations/{id}` | Upravit / deaktivovat lokaci |
| POST | `/api/moves` | Přesunout položku |
| GET/POST | `/api/audits` | Inventury |
| POST | `/api/audits/{id}/scan` | Naskenovat položku |
| POST | `/api/audits/{id}/close` | Uzavřít inventuru |
| GET | `/api/audits/{id}/report` | Zpráva z inventury |
| GET | `/api/qr/item/{id}` | QR kód položky (PNG) |
| GET | `/api/qr/location/{id}` | QR kód lokace (PNG) |
| GET | `/api/qr/batch?ids=1,2,3` | PDF se štítky |
| GET | `/api/export/excel` | Excel export majetku |
| GET | `/api/export/pdf/{audit_id}` | PDF zpráva z inventury |
| GET | `/scan/{item_code}` | Skenování QR kódu |

## Jak používat

### 1. Přidat majetek
Jděte na **Majetek → Přidat**, zadejte kód a název.

### 2. Vytisknout QR štítky
Jděte na **Tisk**, vyberte položky, klikněte **Generovat PDF**.

### 3. Spustit inventuru
**Inventury → Nová inventura** → Skenujte QR kódy telefonem → Uzavřít inventuru.

### 4. Přesunout majetek
Na detailu položky vyberte cílovou lokaci a klikněte **Přesunout**.

### 5. Spravovat uživatele
Jako admin jděte na **Uživatelé** v levém menu.

## Prostředí (.env)

```env
APP_ENV=development          # development / production
BASE_URL=http://localhost:8000
SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///./data/inventory.db
FIRST_ADMIN_USER=admin
FIRST_ADMIN_PASS=admin123
```

## Datový model

```
users → locations → assignments (append-only, aktuální lokace = poslední záznam)
      → items → assignments
               → disposals
      → audits → audit_scans (unique: audit_id + item_id)
```

Kritická pravidla:
- **assignments je append-only** — nikdy se neupdatuje, jen vkládá
- **Soft delete** — položky se označí `is_active=False`, nikdy fyzicky nemazat

## Testy

```bash
make test       # 99 testů
make test-unit  # jen unit testy modelů
make test-api   # jen API testy
```
