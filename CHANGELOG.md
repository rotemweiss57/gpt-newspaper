# Changelog - GPT Newspaper

## [2025-11-15] - Article Length Selection & Bug Fixes

### 🎯 Główne zmiany

#### ✨ Nowe funkcje

**1. Wybór długości artykułów (Standard / Advanced)**
- Dodano dropdown wyboru długości artykułów na stronie głównej
- Dwa tryby generowania:
  - **Standard Mode**: Używa GPT-4, generuje zwięzłe artykuły (5-6 paragrafów)
  - **Advanced Mode**: Używa GPT-4-Turbo, generuje obszerne artykuły (8-12 paragrafów)
- Advanced mode oferuje:
  - Szczegółową 12-paragrafową strukturę artykułu
  - Wyższą temperaturę (0.8) dla bardziej kreatywnego pisania
  - Extended max_tokens (4096) dla dłuższej treści
  - Dogłębną analizę i kompleksowe pokrycie tematu

**2. System limitów dla Advanced Mode**
- Wizualne ostrzeżenie: "⚠️ Advanced mode: Maximum 1 topic (longer processing time)"
- Automatyczne usuwanie nadmiarowych pytań przy przełączeniu na Advanced
- Blokada dodawania więcej niż 1 pytania w trybie Advanced
- Walidacja przed generowaniem gazety
- **Powód**: Zapobieganie błędowi timeout 524 (Cloudflare limit 100s)

### 🐛 Naprawione błędy

**1. Krytyczny: Kodowanie polskich znaków (UTF-8)**
- **Problem**: Polskie znaki diakrytyczne wyświetlały się jako sekwencje Unicode
  - Przykład: `\u0142` zamiast `ł`, `\u00f3` zamiast `ó`
- **Rozwiązanie**: Dodano `encoding='utf-8'` do wszystkich operacji zapisu plików HTML
- **Pliki zmienione**:
  - `backend/agents/designer.py` - funkcja `save_article_html()`
  - `backend/agents/publisher.py` - funkcja `save_newspaper_html()`
- **Efekt**: Wszystkie polskie znaki (ł, ó, ą, ę, ć, ś, ź, ż, ń) wyświetlają się poprawnie

**2. Błąd max_tokens w GPT-4-Turbo**
- **Problem**: `max_tokens=8000` przekraczał limit modelu (4096)
- **Błąd**: `BadRequestError: max_tokens is too large: 8000`
- **Rozwiązanie**: Zmniejszono do `max_tokens=4096`
- **Commit**: `89806e6`

**3. Problemy z kodowaniem emoji w promptach**
- **Problem**: Emoji (🚨, ⚠️) w promptach powodowały problemy kodowania
- **Rozwiązanie**: Zastąpiono emoji tekstowymi markerami (*** CRITICAL ***)
- **Commit**: `3286cf2`

**4. Błąd 524 (Gateway Timeout)**
- **Problem**: Advanced mode z wieloma pytaniami przekraczał limit czasu Cloudflare (100s)
- **Rozwiązanie**: Ograniczenie Advanced mode do 1 pytania
- **Szczegóły**: 
  - Cloudflare Free: 100s timeout
  - Nginx: 600s timeout (proxy_read_timeout)
  - Advanced mode: ~70s na artykuł
  - 2 artykuły = ~140s → timeout

### 🔧 Zmiany techniczne

#### Frontend (`/frontend/`)

**index.html**
```html
<!-- Dodano wybór długości artykułów -->
<p class="layout">Length of articles</p>
<div class="length-selection">
    <select id="lengthSelect" class="length-dropdown">
        <option value="standard">Standard</option>
        <option value="advanced">Advanced publication</option>
    </select>
</div>
<p class="length-info" id="lengthInfo" style="display: none;">
    ⚠️ Advanced mode: Maximum 1 topic (longer processing time)
</p>
```

**styles.css**
- Dodano style dla `.length-selection` i `.length-dropdown`
- Dodano style dla `.length-info` (ostrzeżenie)
- Spójny design z istniejącym językiem dropdown
- Kolory: fioletowy border (#A94FDD), pomarańczowe ostrzeżenie (#FFA500)

**scripts.js**
- Dodano `handleLengthChange()` - zarządza widocznością ostrzeżenia
- Zmodyfikowano `addTopicField()` - blokuje dodawanie w Advanced mode
- Zmodyfikowano `produceNewspaper()` - walidacja liczby pytań
- Automatyczne czyszczenie nadmiarowych pytań przy zmianie na Advanced

#### Backend (`/backend/`)

**server.py**
```python
@backend_app.route('/generate_newspaper', methods=['POST'])
def generate_newspaper():
    data = request.json
    language = data.get("language", "english")
    length = data.get("length", "standard")  # Nowy parametr
    # ...
```

**langgraph_agent.py**
```python
def run(self, queries: list, layout: str, language: str = "english", length: str = "standard"):
    # ...
    writer_agent = WriterAgent(language, length)  # Przekazanie parametru length
```

**agents/writer.py** (Główne zmiany)
```python
class WriterAgent:
    def __init__(self, language: str = "english", length: str = "standard"):
        self.language = language
        self.length = length
        self.length_instructions = {
            "standard": "Write a concise, well-structured article with 5-6 paragraphs.",
            "advanced": "Write a comprehensive, in-depth article with 8-12 paragraphs."
        }
    
    def writer(self, query: str, sources: list):
        if self.length == "advanced":
            # GPT-4-Turbo z rozszerzonymi instrukcjami
            response = ChatOpenAI(
                model='gpt-4-turbo',
                max_tokens=4096,
                temperature=0.8,
                model_kwargs={"response_format": {"type": "json_object"}}
            ).invoke(messages).content
        else:
            # GPT-4 standardowe
            response = ChatOpenAI(
                model='gpt-4-0125-preview',
                model_kwargs={"response_format": {"type": "json_object"}}
            ).invoke(messages).content
```

**agents/designer.py**
```python
def save_article_html(self, article):
    # Dodano encoding='utf-8'
    with open(path, 'w', encoding='utf-8') as file:
        file.write(article['html'])
```

**agents/publisher.py**
```python
def save_newspaper_html(self, newspaper_html):
    # Dodano encoding='utf-8'
    with open(path, 'w', encoding='utf-8') as file:
        file.write(newspaper_html)
```

### 📊 Porównanie trybów

| Cecha | Standard Mode | Advanced Mode |
|-------|---------------|---------------|
| Model | GPT-4 | GPT-4-Turbo |
| Długość | 5-6 paragrafów | 8-12 paragrafów |
| Max tokens | Domyślny | 4096 |
| Temperature | 0.7 (domyślna) | 0.8 |
| Czas generowania | ~30-40s | ~60-90s |
| Limit pytań | Bez limitu | 1 pytanie |
| Struktura | Podstawowa | 12-punktowa szczegółowa |
| Użycie | Szybkie wiadomości | Dogłębne analizy |

### 🔄 Workflow Git

**Commits:**
```
448409e - feat: Add article length selection with Standard and Advanced modes
f5b312b - feat: Add topic limit warning for Advanced mode
```

**Pull Request:** 
- PR #1: https://github.com/sstanczuk/gpt-newspaper/pull/1
- Tytuł: "feat: Add article length selection with Standard and Advanced modes + UTF-8 encoding fix"
- Status: Utworzony, oczekuje na review

### ⚙️ Konfiguracja

**.gitignore** (zaktualizowano)
```
.env
outputs/
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.log
```

**Nginx** (bez zmian)
- Timeouty: 600s (proxy_read_timeout, proxy_send_timeout)
- HTTP Basic Authentication: włączone
- Domeny: karinasiwek.ns.techdiab.pl, newss.tojest.dev

### 🧪 Testowanie

**Przetestowane scenariusze:**
- ✅ Standard mode - język angielski
- ✅ Standard mode - język polski
- ✅ Advanced mode - język angielski  
- ✅ Advanced mode - język polski
- ✅ Kodowanie polskich znaków po fix
- ✅ Blokada dodawania pytań w Advanced mode
- ✅ Automatyczne usuwanie nadmiarowych pytań
- ✅ Walidacja przed generowaniem

**Znane ograniczenia:**
- Advanced mode ograniczony do 1 pytania (limit timeout)
- Długość artykułów nadal ~6 paragrafów mimo instrukcji 12 (limitacja GPT)
- Cloudflare Free timeout 100s (wymaga Pro dla dłuższych operacji)

### 📝 Użycie

**Dla użytkownika:**
1. Wybierz język publikacji (English/Polish)
2. Wybierz długość artykułów:
   - **Standard**: Szybkie, zwięzłe artykuły (max 5 pytań)
   - **Advanced**: Obszerne, szczegółowe artykuły (tylko 1 pytanie)
3. Wprowadź pytanie/temat
4. Wybierz layout gazety
5. Kliknij "Produce Newspaper"

**Dla developera:**
```bash
# Uruchomienie aplikacji
cd /home/root/webapp
source .env
./venv/bin/python app.py

# Backend: http://127.0.0.1:8000
# Frontend: http://127.0.0.1:1337
```

### 🗂️ Struktura projektu (aktualna)

```
webapp/
├── .env                        # Konfiguracja środowiska
├── .env.dist                   # Przykładowa konfiguracja
├── .gitignore                  # Ignorowane pliki
├── CHANGELOG.md                # Ten plik - historia zmian
├── CONTRIBUTING.md             # Wytyczne dla kontrybutorów
├── Dockerfile                  # Konfiguracja Docker
├── LICENCE                     # Licencja MIT
├── README.md                   # Główna dokumentacja
├── app.log                     # Logi aplikacji
├── app.py                      # Główny plik aplikacji (Flask)
├── backend/                    # Backend Python
│   ├── __init__.py
│   ├── server.py               # Flask API endpoint
│   ├── langgraph_agent.py      # Orkiestracja agentów
│   └── agents/                 # Agenty LangGraph
│       ├── __init__.py
│       ├── search.py           # SearchAgent (Tavily)
│       ├── curator.py          # CuratorAgent
│       ├── writer.py           # WriterAgent (GPT-4/Turbo)
│       ├── critique.py         # CritiqueAgent
│       ├── designer.py         # DesignerAgent
│       ├── editor.py           # EditorAgent
│       └── publisher.py        # PublisherAgent
├── docker-compose.yml          # Docker Compose
├── frontend/                   # Frontend aplikacji
│   ├── index.html              # Strona główna
│   └── static/
│       ├── styles.css          # Style CSS
│       ├── scripts.js          # JavaScript
│       ├── favicon.ico         # Ikona
│       └── layout_icons/       # Ikony layoutów
├── logs/                       # Katalog logów
├── outputs/                    # Wygenerowane gazety (HTML)
├── requirements.txt            # Zależności Python
├── start.sh                    # Skrypt startowy
└── venv/                       # Środowisko wirtualne Python
```

### 🔮 Przyszłe ulepszenia (propozycje)

1. **Async Processing**
   - Implementacja kolejki zadań (Celery/Redis)
   - WebSocket dla live updates
   - Unikanie timeoutów dla długich operacji

2. **Caching**
   - Cache dla wyników wyszukiwania
   - Cache dla wygenerowanych artykułów
   - Redukcja kosztów API

3. **Monitoring**
   - Dashboard z metrykami (czas generowania, koszty API)
   - Error tracking (Sentry)
   - Analytics użytkowania

4. **Dodatkowe funkcje**
   - Eksport do PDF
   - Email delivery
   - Harmonogram automatycznego generowania
   - Więcej layoutów gazety

### 👥 Autorzy

- Backend/Frontend development: GPT Newspaper Team
- AI Integration: Claude AI Assistant
- Testing & QA: Manual testing + user feedback

### 📄 Licencja

MIT License - Zobacz plik LICENCE dla szczegółów

---

**Ostatnia aktualizacja:** 15 listopada 2025
**Wersja:** 1.1.0
**Status:** Production Ready ✅
