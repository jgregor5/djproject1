# Activitat: Tests funcionals amb Playwright

Adaptació de l'activitat original (Selenium + Django) per utilitzar **Playwright** com a eina d'automatització del navegador.

---

## Objectius

- Implementar tests funcionals automatitzats en un projecte Django.
- Utilitzar Playwright per controlar el navegador i verificar el comportament de l'aplicació.
- Executar els tests en mode headless.
- Versionar els canvis amb Git.

---

## Eines i tecnologies

- **Django** (projecte existent)
- **Playwright** – biblioteca d'automatització de navegadors (substitueix Selenium)
- **pytest** + **pytest-django** + **pytest-playwright**
- **Python Virtual Environment**
- **Git**

---

## Passos

### 1. Crear l'aplicació Django (si no existeix)

```bash
./manage.py startapp myapp
```

Afegir `myapp` a `INSTALLED_APPS` dins `djproject1/settings.py`.

---

### 2. Instal·lar les dependències

```bash
pip install pytest pytest-django pytest-playwright
playwright install
pip freeze > requirements.txt
```

> `playwright install` descarrega els navegadors (Chromium, Firefox, WebKit). No cal instal·lar cap driver manualment.

---

### 3. Configurar pytest per a Django

Crear el fitxer `pytest.ini` a l'arrel del projecte:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = djproject1.settings
```

---

### 4. Configurar la base de dades de test

Afegir la clau `TEST` a `DATABASES` dins `djproject1/settings.py` perquè els tests usin sempre una BD en memòria, independent de la BD de producció:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'TEST': {
            'NAME': ':memory:',
        },
    }
}
```

> Sense aquest ajust, en màquines on la BD de producció ja té dades, els tests poden fallar amb errors de clau duplicada.

---

### 5. Crear la base de dades de test (fixtures)

```bash
./manage.py createsuperuser --username isard
mkdir -p myapp/fixtures
./manage.py dumpdata --natural-foreign --exclude contenttypes --exclude auth.permission > myapp/fixtures/testdb.json
```

> Cal excloure `contenttypes` i `auth.permission` perquè Django els crea automàticament en la BD de test. Si s'inclouen al fixture es produeix un error de clau duplicada.

---

### 5. Crear el fitxer conftest.py

Crear el fitxer `conftest.py` a l'arrel del projecte:

```python
import os
import pytest

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    with django_db_blocker.unblock():
        from django.test.utils import setup_databases
        from django.core.management import call_command
        setup_databases(verbosity=0, interactive=False)
        call_command("loaddata", "myapp/fixtures/testdb.json")
```

> `DJANGO_ALLOW_ASYNC_UNSAFE=true` és necessari perquè pytest-playwright executa els tests dins d'un event loop asíncron, i Django per defecte rebutja operacions síncrones de BD en aquest context.
>
> `setup_databases()` crea la BD de test (en memòria si s'ha configurat `TEST: {'NAME': ':memory:'}`) i aplica totes les migracions. Cal cridar-ho explícitament perquè estem sobreescrivint el `django_db_setup` de pytest-django. Sense aquesta crida, `migrate` s'executaria contra la BD de producció en lloc de la BD de test.
>
> `loaddata` carrega el fixture un cop la BD de test ja existeix i té les taules creades.

---

### 6. Escriure els tests

Crear els directoris i el fitxer de tests:

```bash
mkdir -p myapp/tests
touch myapp/tests/__init__.py
```

Crear el fitxer `myapp/tests/test_functional.py`:

```python
import pytest


@pytest.mark.django_db(transaction=True)
class TestAdminLogin:

    def test_login(self, page, live_server):
        """Comprova que l'administrador pot iniciar sessió correctament."""
        page.goto(f"{live_server.url}/admin/login/")
        page.fill("#id_username", "isard")
        page.fill("#id_password", "pirineus")
        page.click("[type=submit]")

        assert page.url == f"{live_server.url}/admin/"

    def test_login_error(self, page, live_server):
        """Comprova que credencials incorrectes no permeten l'accés."""
        page.goto(f"{live_server.url}/admin/login/")
        page.fill("#id_username", "isard")
        page.fill("#id_password", "contrasenya_incorrecta")
        page.click("[type=submit]")

        assert page.url != f"{live_server.url}/admin/"
```

**Diferències respecte a Selenium:**

| Selenium | Playwright |
|---|---|
| `StaticLiveServerTestCase` | `live_server` fixture de pytest-django |
| `setUpClass` / `tearDownClass` | Fixtures de pytest (`page`, `browser`) |
| `driver.find_element(By.ID, ...)` | `page.fill("#id_...")` |
| `driver.get(url)` | `page.goto(url)` |
| `WebDriverWait` per esperar elements | Espera automàtica integrada |

---

### 7. Executar els tests

```bash
pytest myapp/tests/test_functional.py -v
```

> Cal executar-ho amb el venv activat (`source venv/bin/activate`) o usant directament `venv/bin/pytest`.

**Mode amb finestra visible** (per depurar):

```bash
pytest myapp/tests/test_functional.py -v --headed
```

> Per defecte, Playwright ja executa en mode headless (sense finestra). No cal cap variable d'entorn com `MOZ_HEADLESS=1`.

**Triar navegador** (per defecte Chromium):

```bash
pytest myapp/tests/test_functional.py --browser firefox
pytest myapp/tests/test_functional.py --browser webkit
```

---

### 8. Configurar GitHub Actions (CI)

Crear el fitxer `.github/workflows/django.yml`:

```yaml
name: Django CI

on:
  push:
    branches: [ "master" ]
  pull_request:
    branches: [ "master" ]

jobs:
  build:

    runs-on: ubuntu-latest
    strategy:
      max-parallel: 4
      matrix:
        python-version: ["3.12"]

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install Dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Cache Playwright Browsers
      uses: actions/cache@v4
      id: playwright-cache
      with:
        path: ~/.cache/ms-playwright
        key: playwright-chromium-${{ hashFiles('requirements.txt') }}
    - name: Install Playwright Browsers
      if: steps.playwright-cache.outputs.cache-hit != 'true'
      run: playwright install --with-deps chromium
    - name: Install Playwright System Dependencies
      if: steps.playwright-cache.outputs.cache-hit == 'true'
      run: playwright install-deps chromium
    - name: Run Tests
      run: |
        pytest myapp/tests/test_functional.py -v
```

**Notes importants respecte al workflow Selenium original:**

| Selenium | Playwright |
|---|---|
| `MOZ_HEADLESS=1` a l'env | No cal (headless per defecte) |
| `python manage.py test` | `pytest myapp/tests/test_functional.py -v` |
| No cal instal·lar navegador | Cal `playwright install --with-deps chromium` |
| `actions/setup-python@v3` | `actions/setup-python@v5` |

> Usar la **cache** dels navegadors (`actions/cache@v4`) és essencial: sense ella, cada execució del CI descarrega ~290 MB de Chromium, cosa que causa timeouts.

---

### 9. Versionar els canvis

```bash
git add myapp/tests/ myapp/fixtures/ conftest.py pytest.ini requirements.txt .github/
git commit -m "Afegir tests funcionals amb Playwright"
git push
```

---

## Diferències principals respecte a la versió amb Selenium

| Aspecte | Selenium | Playwright |
|---|---|---|
| Instal·lació del navegador | Manual (Firefox ESR, chromedriver...) | `playwright install` ho gestiona tot |
| Mode headless | `MOZ_HEADLESS=1` o opcions del driver | Headless per defecte |
| Espera d'elements | `WebDriverWait` explícit | Auto-wait integrat |
| Compatibilitat amb snap | Problemes coneguts | Sense problemes |
| Estructura de tests | `unittest.TestCase` | pytest + fixtures |
| Navegadors suportats | Firefox, Chrome | Chromium, Firefox, WebKit |
