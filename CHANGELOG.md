# CHANGELOG — AssetTrack

## [1.6.8] — 2026-03-09

### Výkon & SEO (Lighthouse audit)

- **Meta description** — přidán `<meta name="description">` do `base.html` s přepisovatelným `{% block meta_description %}`; opravuje SEO audit score
- **HTTP/2** — zapnut `http2 on;` v `nginx/nginx.conf`; zlepšuje latenci multiplexováním požadavků
- **Statické soubory přes nginx** — `/static/` a `/favicon/` servovány přímo nginxem (ne přes proxy na FastAPI); `expires 1y` + `Cache-Control: public, immutable`; do `docker-compose.yml` přidány volume mounty `./app/static:/srv/static:ro` a `./favicon:/srv/favicon:ro`
- **Kontrast barev** — zvýšen kontrast sekundárního textu `--t3` pro splnění WCAG AA (4.5:1): dark téma `#636363 → #808080`, light téma `#999999 → #666666`
- **Minifikace CSS** — `app.css` minifikován (32 KB → 26 KB, −20%); verze bumped na `?v=8`
- **Render-blocking scripty** — `html5-qrcode.min.js` a `scan.js` přesunuty z `<head>` (blokující) do `{% block scripts %}` na konci `<body>` ve `scan/index.html`

---

## [1.6.7] — 2026-03-06

### Branding

- **Favicon** — přidána sada favikon (`favicon/`) servovaná přes `/favicon/` mount; `base.html` obsahuje `<link>` tagy pro `favicon.ico`, `favicon-16x16.png`, `favicon-32x32.png`, `apple-touch-icon.png` a `site.webmanifest`; `site.webmanifest` aktualizován s názvem aplikace, tmavými barvami a správnými cestami
- **Logo v README** — SVG logo přidáno na začátek `README.md`

---

## [1.6.5] — 2026-03-05

### Bezpečnostní opravy (CWE-601 — Open Redirect)

- **`auth_ui.py` — odstraněn parametr `next`** — login formulář přijímal `next` jako POST field (původně z `?next=` query stringu); útočník mohl poslat odkaz `/login?next=//evil.com` a po přihlášení přesměrovat oběť na cizí doménu; parametr odstraněn, po přihlášení se vždy přesměruje na `/`; odstraněny i `_safe_next()` helper, `urlparse` import a hidden field v `login.html`
- **`scan.py` — `code` nahrazen `item.code`** — path parametr `code` (user input) tékl přímo do redirect URL pro sken inventury; nahrazen `item.code` z databáze; funkčně identické, žádný user input v redirect cíli

---

## [1.6.4] — 2026-03-05

### UI

- **Verze v sidebaru** — zobrazovaná verze (`vX.X`) se nyní čte přímo z `app.version` v `main.py` přes Jinja2 globál; patch číslo je automaticky ořezáno; při bumpu verze stačí měnit jediné místo

### QR štítky

- **Štítek majetku — QR velikost** — snížen `border` z 4 na 1 modul; viditelný vzor QR nyní odpovídá definované hodnotě `qr_size=16 mm` (dříve ~13 mm kvůli bílému okraji)

### Opravené problémy

- **Filtr kategorie — HTMX 422** — `hx-include` pro vyhledávání a filtry byl stránkový (bez prefixu), čímž zachytával i stejnojmenná pole `name` a `category` v modálech (přidávání položky); FastAPI přijímal duplicitní parametry a vracel 422; opraveno scoped selektorem `.search-row [name='...']`
- **Filtr kategorie — case-insensitive** — shoda kategorie v `item_service.py` změněna z `==` na `.ilike()` pro odolnost vůči různé velikosti písmen

---

## [1.6.3] — 2026-03-05

### Správa majetku

- **Filtr "Nepřiřazeno"** — dropdown místností v seznamu majetku obsahuje novou volbu `— Nepřiřazeno`; zobrazí jen položky bez jakéhokoli přiřazení k lokaci
- **Oprava vyhledávání** — HTMX search selhal kvůli `location_id=` (prázdný řetězec) interpretovaného FastAPI jako neplatný `int`; výchozí option dropdownu změněn na `value="0"`, search nyní funguje správně

### Správa lokací

- **Hromadný přesun položek** — nový endpoint `POST /api/moves/bulk`; přesune všechny položky z jedné lokace do druhé (jeden API call); UI tlačítko "Přesunout položky z jiné lokace" na detailu lokace
- **Přiřazení nepřiřazených položek** — nový endpoint `POST /api/moves/assign-unlocated/{loc_id}`; přiřadí sem všechny položky bez viditelné lokace (bez assignment + položky s assignment → neaktivní lokaci); UI banner na detailu lokace s počtem a tlačítkem "Přiřadit sem vše"

---

## [1.6.2] — 2026-03-05

### QR štítky

- **Štítek lokace — záhlaví** — modrý header zobrazuje **název místnosti** (`loc.name`) s auto-fit fontem; kód lokace zůstává pod QR kódem
- **Štítek lokace — pod QR** — název místnosti odstraněn (je v záhlaví); zobrazuje se jen kód lokace
- **Štítek lokace — šířka** — šířka štítku rozšířena z 30 mm na 45 mm; auto-fit font pro záhlaví i kód pod QR
- **Štítek majetku — nové rozložení** — QR kód vlevo + kód majetku vpravo vedle sebe, výška štítku **2 cm**; název položky na štítku odstraněn; kód auto-fit na dostupnou šířku
- **Štítek majetku — velikost** — šířka 55 mm × výška 20 mm; QR čtverec 16 × 16 mm vertikálně vystředěn
- **UI — verze** — verze v sidebaru zobrazena ve formátu `X.X` (bez patch čísla)

---

## [1.6.1] — 2026-03-04

### Opravené problémy

- **Majetek — šířky sloupců** — tabulka majetku dostala CSS třídu `tbl--items` s pevnými šířkami sekundárních sloupců (Kód 130px, Lokace 160px, Kategorie 120px, Pořízeno 80px); sjednoceno s logikou tabulky lokací (`tbl--loc`)
- **Přetečení textu** — sloupce Lokace a Kategorie v tabulce majetku oříznuty pomocí `text-overflow: ellipsis`; stejné ošetření jako u kódu lokace

---

## [1.6.0] — 2026-03-04

### Nové funkce

- **Filtr místností — Majetek** — seznam majetku `/majetek` rozšířen o dropdown filtr místností; filtr funguje přes HTMX live search spolu s existujícím filtrem kategorie a vyhledáváním; paginace zachovává zvolený filtr
- **Filtr místností — Tisk štítků** — záložka „Položky majetku" na `/tisk` obsahuje dropdown filtru místností; zobrazí pouze položky z vybrané místnosti; nový sloupec „Místnost" v tabulce; tlačítko „Vybrat viditelné" vybere jen filtrované řádky
- **Filtr budov — Tisk štítků (lokace)** — záložka „Lokace / Místnosti" na `/tisk` obsahuje dropdown filtru budov; zobrazí pouze lokace z vybrané budovy
- **Lokace — oprava šířek sloupců** — tabulky lokací seskupené podle budov nyní mají konzistentní šířky sloupců napříč skupinami (CSS třída `tbl--loc` s pevnými šířkami sloupců 2–5)
- **Přetečení kódu lokace** — `.id-badge` v sloupci kódu oříznut na 110 px s `text-overflow: ellipsis`; zabrání rozlití layoutu u dlouhých kódů

### QR štítky

- **Velikost QR kódu** — hromadný tisk štítků (`/api/qr/batch`) upraven: QR kód nyní **2 × 2 cm** (dříve 3,3 / 3,5 cm); štítek položky 30 × 35 mm, štítek lokace 30 × 40 mm

---

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
