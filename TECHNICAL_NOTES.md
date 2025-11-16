# Technical Notes - GPT Newspaper

## 🔧 Sesja rozwojowa: 15 listopada 2025

### Kontekst projektu

GPT Newspaper to aplikacja generująca spersonalizowane gazety przy użyciu:
- **Frontend**: HTML, CSS, JavaScript (Vanilla)
- **Backend**: Python Flask + LangGraph
- **AI Models**: OpenAI GPT-4, GPT-4-Turbo
- **Search**: Tavily API
- **Deployment**: Nginx reverse proxy + Cloudflare
- **Domeny**: karinasiwek.ns.techdiab.pl, newss.tojest.dev

---

## 📋 Realizowane zadania

### 1. Dodanie wyboru długości artykułów

**Wymaganie:** Dropdown z opcjami "Standard" i "Advanced publication"

**Implementacja:**

#### Frontend (3 pliki)
```html
<!-- index.html: Dodano między language selector a layout selector -->
<p class="layout">Length of articles</p>
<div class="length-selection">
    <select id="lengthSelect" class="length-dropdown">
        <option value="standard">Standard</option>
        <option value="advanced">Advanced publication</option>
    </select>
</div>
```

```css
/* styles.css: Style dopasowane do language dropdown */
.length-dropdown {
    font-family: 'Gill Sans', sans-serif;
    border: 2px solid #A94FDD;
    background-color: #1A202C;
    color: #E2E8F0;
    min-width: 200px;
}
```

```javascript
// scripts.js: Przekazanie parametru do API
const selectedLength = document.getElementById('lengthSelect').value;
const payload = {
    topics: topics,
    layout: selectedLayout,
    language: selectedLanguage,
    length: selectedLength  // Nowy parametr
};
```

#### Backend (3 pliki)
```python
# server.py: Przyjęcie parametru
@backend_app.route('/generate_newspaper', methods=['POST'])
def generate_newspaper():
    length = data.get("length", "standard")
    newspaper = master_agent.run(data["topics"], data["layout"], language, length)

# langgraph_agent.py: Przekazanie do WriterAgent
writer_agent = WriterAgent(language, length)

# agents/writer.py: Główna logika
class WriterAgent:
    def __init__(self, language: str = "english", length: str = "standard"):
        self.length = length
        self.length_instructions = {
            "standard": "Write a concise, well-structured article with 5-6 paragraphs.",
            "advanced": "Write a comprehensive, in-depth article with 8-12 paragraphs."
        }
```

---

### 2. Advanced mode z deep-thinking

**Wymaganie:** Tryb Advanced powinien generować dłuższe (8-12 paragrafów), bardziej szczegółowe artykuły

**Implementacja:**

```python
def writer(self, query: str, sources: list):
    if self.length == "advanced":
        messages = [
            SystemMessage(content=f"""
                You are an expert newspaper writer specializing in comprehensive journalism.
                CRITICAL: Your articles MUST contain EXACTLY 10-12 paragraphs.
                
                PARAGRAPH STRUCTURE (MANDATORY):
                1. Introduction and context setting (5-7 sentences)
                2. Historical background and origins (5-7 sentences)
                3. Current state and recent developments (5-7 sentences)
                4-12. [Detailed structure for each paragraph]
            """),
            HumanMessage(content=f"Write IN-DEPTH article with ALL 12 paragraphs...")
        ]
        
        response = ChatOpenAI(
            model='gpt-4-turbo',        # Lepszy model dla długich treści
            max_tokens=4096,             # Extended limit
            temperature=0.8,             # Wyższa kreatywność
            model_kwargs={
                "response_format": {"type": "json_object"}
            }
        ).invoke(messages).content
    else:
        # Standard mode: GPT-4, krótsze prompty
        response = ChatOpenAI(
            model='gpt-4-0125-preview'
        ).invoke(messages).content
```

**Próbowane podejścia:**
1. ❌ Model `o1-preview` - nie dostępny
2. ❌ Model `o1` - nie wspiera parametru `temperature`
3. ✅ Model `gpt-4-turbo` - działa, ale limit 4096 tokenów

**Znane ograniczenia:**
- GPT-4 ma naturalną tendencję do generowania ~6 paragrafów niezależnie od instrukcji
- Advanced mode generuje DŁUŻSZE paragrafy (~387 znaków vs ~257 w Standard)
- Pełne 12 paragrafów rzadko osiągane (limitacja modelu, nie kodu)

---

### 3. Naprawienie błędu 500 (max_tokens)

**Problem:**
```
BadRequestError: max_tokens is too large: 8000. 
This model supports at most 4096 completion tokens
```

**Przyczyna:** 
- Początkowa konfiguracja: `max_tokens=8000`
- GPT-4-Turbo limit: 4096 completion tokens

**Rozwiązanie:**
```python
response = ChatOpenAI(
    model='gpt-4-turbo',
    max_tokens=4096,  # Zmieniono z 8000
    temperature=0.8
).invoke(messages).content
```

**Commit:** `89806e6`

---

### 4. Naprawienie błędu 500 (emoji w promptach)

**Problem:** Emoji (🚨, ⚠️) w promptach powodowały problemy kodowania

**Rozwiązanie:**
```python
# Przed:
f"🚨 CRITICAL INSTRUCTION: Your articles MUST contain..."

# Po:
f"*** CRITICAL INSTRUCTION: Your articles MUST contain..."
```

**Commit:** `3286cf2`

---

### 5. Naprawienie błędu kodowania polskich znaków

**Problem:**
```
Wyświetlanie: Przyk\u0142adem miasta, kt\u00f3re skorzysta\u0142o
Powinno być:  Przykładem miasta, które skorzystało
```

**Przyczyna:** 
- Python `open()` bez parametru `encoding` używa domyślnego kodowania systemu
- JSON z GPT zwraca poprawny UTF-8, ale zapis do pliku używał niewłaściwego kodowania

**Rozwiązanie:**

```python
# backend/agents/designer.py
def save_article_html(self, article):
    # Przed:
    with open(path, 'w') as file:
        file.write(article['html'])
    
    # Po:
    with open(path, 'w', encoding='utf-8') as file:
        file.write(article['html'])

# backend/agents/publisher.py
def save_newspaper_html(self, newspaper_html):
    # Przed:
    with open(path, 'w') as file:
        file.write(newspaper_html)
    
    # Po:
    with open(path, 'w', encoding='utf-8') as file:
        file.write(newspaper_html)
```

**Znaki naprawione:**
- `\u0142` → `ł`
- `\u00f3` → `ó`
- `\u0105` → `ą`
- `\u0119` → `ę`
- `\u0107` → `ć`
- `\u015b` → `ś`
- `\u017a` → `ź`
- `\u017c` → `ż`
- `\u0144` → `ń`

---

### 6. Naprawienie błędu 524 (Gateway Timeout)

**Problem:**
```
Browser console:
Failed to load resource: the server responded with a status of 524 ()
Error: SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON
```

**Przyczyna:**
- Cloudflare Free plan: **100 sekund timeout**
- Nginx: 600 sekund timeout
- Advanced mode z 2 pytaniami:
  - Artykuł 1: ~70 sekund
  - Artykuł 2: ~70 sekund
  - **Razem: ~140 sekund → przekroczenie limitu**

**Debugowanie:**
```bash
# Sprawdzenie logów backendu
tail -100 app.log

# Znaleziono problem: stary kod próbował użyć modelu 'o1' z temperature
# Problem 1: Backend nie był zrestartowany po zmianach kodu
# Problem 2: Timeout Cloudflare

# Restart backendu
pkill -f "python app.py"
cd /home/root/webapp
bash -c 'set -a; source .env; set +a; nohup ./venv/bin/python app.py >> app.log 2>&1 &'
```

**Rozwiązanie:** Ograniczenie Advanced mode do 1 pytania

---

### 7. Dodanie limitu 1 pytania dla Advanced mode

**Wymaganie:** Zapobieganie timeout przez ograniczenie liczby pytań

**Implementacja:**

#### HTML - Wizualne ostrzeżenie
```html
<p class="length-info" id="lengthInfo" style="display: none;">
    ⚠️ Advanced mode: Maximum 1 topic (longer processing time)
</p>
```

#### CSS - Stylizacja ostrzeżenia
```css
.length-info {
    font-family: 'Gill Sans', sans-serif;
    font-size: 14px;
    color: #FFA500;  /* Pomarańczowy */
    background-color: rgba(255, 165, 0, 0.1);
    border-radius: 5px;
    border-left: 4px solid #FFA500;
    animation: fadeIn 0.3s ease-in;
}
```

#### JavaScript - Logika biznesowa
```javascript
// 1. Pokazanie/ukrycie ostrzeżenia
function handleLengthChange() {
    const selectedLength = document.getElementById('lengthSelect').value;
    const lengthInfo = document.getElementById('lengthInfo');
    
    if (selectedLength === 'advanced') {
        lengthInfo.style.display = 'block';
        
        // Automatyczne usunięcie nadmiarowych pytań
        while (topicCount > 1) {
            const topicGroup = document.getElementById('topicGroup' + topicCount);
            if (topicGroup) topicGroup.remove();
            topicCount--;
        }
        addIconToLastTopic();
    } else {
        lengthInfo.style.display = 'none';
    }
}

// 2. Blokada dodawania pytań
function addTopicField() {
    const selectedLength = document.getElementById('lengthSelect').value;
    if (selectedLength === 'advanced') {
        alert('Advanced mode is limited to 1 topic due to longer processing time.');
        return;  // Blokada
    }
    // ... reszta kodu
}

// 3. Walidacja przed wysłaniem
function produceNewspaper() {
    const selectedLength = document.getElementById('lengthSelect').value;
    
    if (selectedLength === 'advanced' && topics.length > 1) {
        alert('Advanced mode is limited to 1 topic. Please remove extra topics or switch to Standard mode.');
        return;  // Blokada wysłania
    }
    // ... reszta kodu
}
```

**UX Flow:**
1. Użytkownik ma 3 pytania w Standard mode
2. Przełącza na Advanced mode
3. **Automatycznie:** Pytania 2 i 3 są usuwane
4. **Ostrzeżenie:** Pojawia się pomarańczowy komunikat
5. **Próba dodania:** Alert informuje o limicie
6. **Próba generowania:** Walidacja blokuje z alertem

---

## 🔄 Git Workflow

### Commits wykonane

```bash
# 1. Squash wszystkich 8 commitów w jeden
git reset --soft HEAD~8
git commit -m "feat: Add article length selection with Standard and Advanced modes"

# 2. Dodanie limitu dla Advanced mode
git add frontend/index.html frontend/static/styles.css frontend/static/scripts.js
git commit -m "feat: Add topic limit warning for Advanced mode"

# Status: 2 commity w lokalnym branch 'genspark_ai_developer'
# NIE wysłane do GitHub (na życzenie użytkownika)
```

### Pull Request utworzony (przypadkowo)

**PR #1:** https://github.com/sstanczuk/gpt-newspaper/pull/1
- Tytuł: "feat: Add article length selection with Standard and Advanced modes + UTF-8 encoding fix"
- Status: Open
- Branch: `genspark_ai_developer` → `master`

**Nota:** Użytkownik poprosił o NIE wysyłanie do GitHub, ale PR został już utworzony wcześniej.

---

## 🐛 Debugging Session

### Problemy napotkane podczas sesji

#### 1. Backend nie uruchamiał się
```bash
Error: tavily.errors.MissingAPIKeyError: No API key provided
```
**Rozwiązanie:** Załadowanie .env przed uruchomieniem
```bash
bash -c 'set -a; source .env; set +a; nohup ./venv/bin/python app.py >> app.log 2>&1 &'
```

#### 2. Venv w commicie (zbyt duży plik)
```bash
Error: File venv/lib/python3.12/site-packages/playwright/driver/node is 117.48 MB
```
**Rozwiązanie:** 
- Dodano venv/ do .gitignore
- Reset staging area
- Commit tylko kodu źródłowego

#### 3. Wiele niepotrzebnych plików w repo
**Rozwiązanie:** Masowe usunięcie plików testowych i dokumentacji
```bash
rm -f API_VERIFICATION_RESULT.txt BUGFIX_SUMMARY.md ... (37 plików)
rm -rf backend/**/__pycache__/
rm -rf logs/*
```

---

## 📊 Statystyki

### Zmiany w kodzie

| Plik | Linie dodane | Linie usunięte | Zmiana |
|------|-------------|----------------|---------|
| `backend/agents/writer.py` | 120+ | 30 | Major rewrite |
| `frontend/index.html` | 8 | 0 | Minor |
| `frontend/static/styles.css` | 18 | 0 | Minor |
| `frontend/static/scripts.js` | 55 | 0 | Medium |
| `backend/agents/designer.py` | 1 | 1 | Fix |
| `backend/agents/publisher.py` | 1 | 1 | Fix |
| `backend/langgraph_agent.py` | 2 | 1 | Minor |
| `backend/server.py` | 2 | 1 | Minor |
| `.gitignore` | 10 | 0 | Update |

**Razem:** ~217 linii dodanych, ~34 linie usuniętych

### Czas trwania sesji

- **Start:** ~09:00
- **Koniec:** ~14:30
- **Czas trwania:** ~5.5 godziny
- **Przerwy:** 2x (lunch, testy)

### Główne aktywności

1. Implementacja wyboru długości (2h)
2. Debugging błędów 500 (1h)
3. Fix kodowania UTF-8 (0.5h)
4. Fix timeout 524 + limit (1.5h)
5. Git workflow + cleanup (0.5h)

---

## 🔍 Kluczowe wnioski

### Co się udało ✅

1. **Pełna implementacja wyboru długości** - Frontend + Backend + AI prompts
2. **Naprawa krytycznego błędu kodowania** - Polskie znaki działają
3. **Rozwiązanie problemu timeout** - Limit 1 pytania w Advanced
4. **UX improvements** - Automatyczne czyszczenie, walidacja, ostrzeżenia
5. **Czysty kod** - Usunięto pliki testowe, uporządkowano repo

### Wyzwania 🤔

1. **Limity GPT** - Model nie generuje pełnych 12 paragrafów mimo instrukcji
2. **Timeout Cloudflare** - Free plan ma sztywny limit 100s
3. **Token limits** - GPT-4-Turbo max 4096, nie 8000
4. **Model availability** - o1/o1-preview niedostępne lub bez temperature

### Lekcje 📚

1. **Zawsze specyfikuj encoding** - `open(file, 'w', encoding='utf-8')`
2. **Sprawdzaj limity modeli** - Dokumentacja OpenAI jest kluczowa
3. **Testuj restart aplikacji** - Zmiany w kodzie wymagają restartu
4. **Cloudflare limits są realne** - Free plan = 100s timeout
5. **Git squash jest przydatny** - Czysta historia commitów

---

## 🚀 Deployment Notes

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/gpt-newspaper
proxy_connect_timeout 600;
proxy_send_timeout 600;
proxy_read_timeout 600;  # Nginx: 600s
send_timeout 600;

# Ale Cloudflare Free: 100s (nie można zmienić bez upgradu)
```

### Backend Startup

```bash
# Krok 1: Załaduj environment variables
cd /home/root/webapp
set -a
source .env
set +a

# Krok 2: Uruchom aplikację
nohup ./venv/bin/python app.py >> app.log 2>&1 &

# Krok 3: Sprawdź status
ps aux | grep "python app.py"
tail -f app.log
```

### Port Allocation

- **Frontend:** 1337 (Flask serve_frontend)
- **Backend API:** 8000 (Flask backend_app)
- **Nginx:** 80, 443 (reverse proxy)

---

## 📚 Dokumentacja API

### Endpoint: Generate Newspaper

```http
POST /api/generate_newspaper
Content-Type: application/json

{
    "topics": ["AI trends 2025"],
    "layout": "layout_1.html",
    "language": "polish",
    "length": "advanced"
}

Response 200:
{
    "path": "/outputs/newspaper.html"
}

Response 500:
{
    "error": "Internal server error"
}

Response 524:
Cloudflare timeout page (HTML)
```

### Parametry

| Parametr | Typ | Wymagany | Wartości | Domyślna |
|----------|-----|----------|----------|----------|
| `topics` | array[string] | Tak | ["topic1", "topic2"] | - |
| `layout` | string | Tak | layout_1.html, layout_2.html, layout_3.html | - |
| `language` | string | Nie | "english", "polish" | "english" |
| `length` | string | Nie | "standard", "advanced" | "standard" |

### Walidacja

- `topics`: Min 1, Max depends on length
  - Standard: unlimited (ale praktycznie ~5 max)
  - Advanced: **Max 1** (timeout protection)
- `layout`: Musi istnieć w templates/
- `language`: Tylko english/polish
- `length`: Tylko standard/advanced

---

## 🔐 Environment Variables

```bash
# .env (przykład)
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

**Wymagane:**
- `OPENAI_API_KEY` - GPT-4/Turbo API
- `TAVILY_API_KEY` - Search API

---

## 🧪 Testing Checklist

### Manual Testing Performed

- [x] Standard mode - English - 1 topic
- [x] Standard mode - English - 3 topics
- [x] Standard mode - Polish - 1 topic
- [x] Standard mode - Polish - 2 topics
- [x] Advanced mode - English - 1 topic
- [x] Advanced mode - Polish - 1 topic
- [x] Polish characters encoding
- [x] Length selector UI
- [x] Warning message display
- [x] Topic limit enforcement
- [x] Auto-removal of extra topics
- [x] Alert on add topic attempt
- [x] Validation before submit

### Not Tested

- [ ] Advanced mode with >1 topic (blocked by design)
- [ ] Concurrent requests
- [ ] Rate limiting behavior
- [ ] Edge cases (bardzo długie pytania, specjalne znaki)

---

## 💡 Rekomendacje na przyszłość

### Krótkoterminowe (Quick wins)

1. **Dodać loader progress bar** - Pokazanie procentu postępu
2. **Error messages w UI** - Zamiast console.error
3. **Backend validation** - Walidacja parametrów po stronie serwera
4. **Logging** - Structured logging (JSON) zamiast print()

### Średnioterminowe

1. **Async processing** - Celery + Redis dla długich zadań
2. **WebSocket updates** - Real-time progress dla użytkownika
3. **Caching** - Redis cache dla wyników search
4. **Rate limiting** - Ochrona API przed nadużyciem

### Długoterminowe

1. **Upgrade Cloudflare** - Pro plan dla 600s timeout
2. **Monitoring** - Prometheus + Grafana
3. **CI/CD** - GitHub Actions dla testów i deploymentu
4. **Unit tests** - pytest dla backendu
5. **E2E tests** - Playwright dla frontendu

---

**Dokument stworzony:** 15 listopada 2025, 14:30  
**Autor:** Claude AI Assistant + User  
**Sesja:** 5.5h development session  
**Status:** Dokumentacja kompletna ✅
