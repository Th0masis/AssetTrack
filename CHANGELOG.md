# CHANGELOG — AssetTrack

## [1.5.0] — 2026-02-27

### Nové funkce

- **HTTPS / SSL** — nginx servíruje aplikaci přes HTTPS na portu 8443; self-signed certifikát generován příkazem `make ssl IP=<ip>`; vyžadováno pro QR skener (kamera v prohlížeči nutí secure context)
- **Auto-vytvoření admina** — při prvním startu aplikace se automaticky vytvoří admin uživatel z `FIRST_ADMIN_USER` / `FIRST_ADMIN_PASS` v `.env`; dříve bylo nutné spustit `make seed` ručně

### Opravené problémy

- **Statické soubory za HTTPS proxy** — `url_for('static',...)` generoval `http://` URL na HTTPS stránce → prohlížeč blokoval CSS/JS (mixed content); opraveno na root-relativní cesty `/static/...`
- **Docker bind mount — SQLite** — spuštění bez existující složky `./data` způsobovalo `OperationalError: unable to open database file`; opraveno přidáním `mkdir -p data && chmod 777 data` do `make prod` a `user: "0:0"` v docker-compose
- **Absolute SQLite path** — `DATABASE_URL` v docker-compose nastaven na absolutní cestu `sqlite:////app/data/inventory.db` aby nedocházelo k chybám relativního rozlišení cesty v kontejneru

### Docker & nasazení

- **`entrypoint.sh`** — nový startovací skript; spouští `alembic upgrade head` před uvicornem; DB migrace proběhnou automaticky při každém startu
- **Health check** — `wget` nahrazen `python -c urllib.request`; spolehlivější v Alpine Python image; `start_period` prodloužen na 30 s
- **`docker-compose` → `docker compose`** — Makefile aktualizován na Compose V2 syntaxi
- **`version:` odstraněno** — deprecated pole odstraněno z obou compose souborů
- **Port 80 odebrán** — nginx nyní exposes pouze `8443:443`; port 80 ponechán Traefiku na stejném hostu
- **`ProxyHeadersMiddleware`** — přidán do FastAPI pro správné zpracování `X-Forwarded-Proto` za nginx proxy

---

## [1.4.0] — 2026-02-27

### Nové funkce

- **Zodpovědná osoba** — nové pole `responsible_person` na položce majetku; zobrazeno v detailu, editaci, Excel exportu, protokolu o vyřazení a importní šabloně; migrace `c4d5e6f7a8b9`
- **Přesun při inventuře** — skenování položky v jiné místnosti než je evidovaná automaticky vytvoří přesun (`Assignment`) s poznámkou *„Automatický přesun při inventuře #ID"*
- **PDF inventury — přesunuté položky** — položky přesunuté během inventury jsou v PDF označeny oranžovým řádkem `→ přesunuto z: [původní místnost]`; statistika v hlavičce PDF nově obsahuje počet přesunů
- **Poslední aktivity — rozšíření** — dashboard nyní zobrazuje přesuny, skeny inventury i vyřazení (s důvodem) seřazené chronologicky

### Mobilní UX

- **Lokace — počet položek na mobilu** — v tabulce lokací je sloupec „Položek" viditelný na mobilu; sloupec „Patro" přesunut za něj a na mobilu skryt

### Opravené problémy

- Duplikátní `_reason_labels` v `ui.py` — odstraněno, použita sdílená konstanta `_REASON_LABELS`
- `db.get()` v loop aktivit nahrazen přímým přístupem přes ORM relationship (`a.item`, `s.item`, `d.item`) — čistší kód bez zbytečných volaní
- `_normalize()` v import service — doplněn komentář vysvětlující účel `rstrip("*")`
- PDF protokol o vyřazení — všechny texty nyní používají `_FONT_REGULAR`/`_FONT_BOLD` (česká diakritika); dříve hardcoded Helvetica

### Bezpečnostní opravy (Low)

- **`FIRST_ADMIN_PASS` výchozí hodnota** — `config.py` loguje varování při výchozím `admin123`
- **Flash zprávy** — `{{ message | escape }}` v `partials/flash.html`
- **Excel import limit** — max 2 000 řádků (`_IMPORT_MAX_ROWS = 2000`)

---

## [1.3.0] — 2026-02-27

### Nové funkce
- **Tři úrovně práv** — `admin` (správa uživatelů), `spravce` (veškeré operace), `user` (pouze čtení)
- **Správa uživatelů** — stránka `/admin/uzivatele`: přidání, změna role, aktivace/deaktivace, změna hesla
- **Editace lokací a majetku** — tlačítko úpravy na stránkách detailu i v seznamech (inline modal)
- **Deaktivace lokací** — UI pro označení lokace jako neaktivní s varováním o přiřazených položkách
- **Mobilní přihlášení** — avatar přihlášeného uživatele + tlačítko odhlášení v mobilním topbaru

### Mobilní UX
- Mobilní zařízení funguje jako **scanner** — editační akce jsou na mobilu skryty bez ohledu na roli
- Skryté akce na mobilu: Přesunout, Upravit, Vyřadit (majetek), Upravit, Deaktivovat (lokace), Uzavřít inventuru
- Skryté tlačítka "+ Přidat" v section headerech na mobilu
- Přidány chybějící role-guardy na "+ Přidat položku" a "+ Nová inventura"

### PDF inventury
- Podpora české diakritiky (font DejaVu)
- Rozdělení položek podle místností s oranžovými nadpisy sekcí
- Hlavička s metadaty (název, kdo zahájil, kdo uzavřel, datum, stav)
- Sekce chybějících položek zvýrazněna červeně
- Patička se stránkováním a časem tisku
- Pole `closed_by` na modelu `Audit` (FK → users)

### Bezpečnostní hardening (security audit 2026-02-27)

#### Opraveno — Critical
- **Neautentizovaná API** — `POST /api/audits`, `POST /api/audits/{id}/scan`, `POST /api/audits/{id}/close`, `GET /api/disposals` byly přístupné bez přihlášení → přidány dependency `require_session_user` / `require_session_manager`
- **Hardcoded `SYSTEM_USER_ID = 1`** — inventury se vždy přiřazovaly user ID 1 → `user_id` se nyní čte ze session přihlášeného uživatele

#### Opraveno — High
- **CSRF ochrana** — všechny HTML POST formuláře (správa uživatelů, změna hesla, deaktivace lokace) nyní obsahují CSRF token generovaný ze session; endpointy ho verifikují přes `verify_csrf` dependency
- **Session cookie flags** — přidány `same_site="lax"` a `https_only=True` v produkci (`APP_ENV=production`)
- **Rate limiting na loginu** — max 10 neúspěšných pokusů za 60 s per IP; po úspěšném přihlášení se čítač resetuje
- **Open redirect** — `?next=//attacker.com` procházelo kontrolou `startswith("/")` → nahrazeno `_safe_next()` odmítající URL se `scheme` nebo `netloc`
- **Výchozí SECRET_KEY** — `"change-me-in-production"` způsobuje `RuntimeError` při `APP_ENV=production`; v dev režimu pouze varování v logu
- **Security headers** — přidán `SecurityHeadersMiddleware`: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Strict-Transport-Security` (pouze produkce)

#### Opraveno — Medium
- **Surové DB chyby ve flash** — `admin_ui.py` nyní loguje plnou chybu serverově, uživateli zobrazí generickou hlášku; `ValueError` (aplikační chyby, např. duplicitní uživatel) se stále zobrazují
- **`is_active` v update schématech** — odstraněno z `ItemUpdate` a `LocationUpdate`; soft-delete jde výhradně přes DELETE endpoint nebo disposal systém
- **File upload paměť** — přidána kontrola `Content-Length` hlavičky před čtením souboru (early rejection), zálohu tvoří kontrola po načtení
- **Validace kódu a názvu** — `ItemBase.code` max 64 znaků, `ItemBase.name` max 255 znaků; `LocationBase.code` max 32 znaků, `LocationBase.name` max 255 znaků (`Field` s `min_length`/`max_length`)
- **Validace hesla** — `UserCreate.password` min 8 znaků; `UserBase.username` min 2, max 64 znaků
- **Audit log** — přihlášení (úspěch/neúspěch), změna role, vytvoření/aktivace/deaktivace uživatele logováno přes Python `logging` s prefixem `AUDIT:`
- **`/scan/{code}` a `/api/scan/resolve/{code}` bez autentizace** — přidány `require_user` resp. `require_session_user`

#### Opraveno — Low
- **`FIRST_ADMIN_PASS` výchozí hodnota** — `config.py` nyní loguje varování při výchozím `admin123`; v produkci úroveň WARNING
- **Flash zprávy** — `partials/flash.html` nyní používá `{{ message | escape }}` pro prevenci XSS
- **Excel import limit** — max 2 000 řádků na import (`_IMPORT_MAX_ROWS = 2000`); překročení vrací chybu před načtením dat

#### Zbývá — Low (není opraveno)
- `pip-audit` nebyl spuštěn pro kontrolu CVE v závislostech

### Opravené problémy
- `get_flashed_messages` nedostupné v admin šablonách — admin router nyní sdílí instanci `templates` s UI routerem
- QR sekce v detailu majetku přetékala na mobilu — nové CSS třídy `.qr-card`, `.qr-url` s `word-break: break-all`

---

## [1.2.0] — 2026-02-25

### Nové funkce
- **Přihlašování** — session-based autentizace (login/logout), všechny UI routy chráněny
- **Vyřazení majetku** — model `Disposal`, endpoint `POST /api/items/{id}/dispose`, `GET /api/disposals`, hromadné vyřazení
- **Import z Excelu** — stránka `/import`, šablona ke stažení, endpoint `POST /import`
- **QR scanner** — stránka `/sken` s kamerou (html5-qrcode lokálně)
- **Tisk QR štítků** — PDF štítky pro položky (50×48 mm) a lokace (60×56 mm)

### Redesign frontendu (v3)
- Odstraněn Bootstrap — vlastní CSS design system (BEZ CDN)
- Typografie: IBM Plex Sans / IBM Plex Mono (fonty lokálně, WOFF2)
- Barva: oranžový akcent `#F07800`, tmavé/světlé téma (`data-theme`)
- Dvoubarevné logo: `Asset` (oranžová) + `Track` (neutrální)
- Přepínač dark/light motivu (sidebar + mobilní topbar, `localStorage`)
- Anti-flash script před načtením CSS
- HTMX lokálně (`app/static/js/htmx.min.js`)
- Mobile-first layout: sidebar desktop, bottom-nav mobil

### Vylepšení
- Přidání položky: formulář obsahuje lokaci, popis, datum nákupu, cenu
- Excel export: sloupce kód/název místnosti v listu Majetek i Historie přesunů, styled hlavičky
- Lokace: zobrazení počtu aktuálně přiřazených položek
- Dashboard: aktivní inventura zobrazuje správný progress
- Poslední aktivity: přepracovány na standardní `.tbl` tabulku

### Testy
- **99 testů, 100% zelené**

---

## [1.1.0] — 2026-02-22

### Nové funkce
- HTMX live search na stránce majetku
- Progress bar inventury (HTMX partial update)
- HTMX partial `/majetek/search`
- Scan feedback přes partial update

### Opravené problémy
- Scan stránka: fix `defer` bug způsobující neinicializaci QR skeneru
- Mobilní layout: opravy zobrazení na 375px

---

## [1.0.0] — 2026-02-20

### Nové funkce
- Správa majetku (CRUD) — kódy, kategorie, sériová čísla, ceny
- Správa lokací — budova, patro, kód
- Přesuny majetku — append-only záznamy v `assignments`
- Inventury (audity) — vytvoření, skenování, uzavření, report
- QR kódy pro položky a lokace (PNG)
- Dávkový tisk QR štítků do PDF
- Export majetku do Excelu (.xlsx) s historií přesunů
- Export inventury do PDF
- FastAPI REST API s Pydantic validací a Swagger UI

### Opravené problémy
- `bcrypt` 5.x není kompatibilní s `passlib` — pin na `bcrypt==4.0.1`
- SQLite in-memory DB v testech vyžaduje `StaticPool`
