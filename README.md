# BravoBot — Asistente Inteligente I.U. Pascual Bravo

Chatbot conversacional basado en RAG (Retrieval-Augmented Generation) para aspirantes de la Institución Universitaria Pascual Bravo. Responde preguntas sobre programas académicos, admisiones, costos, bienestar y becas usando exclusivamente información oficial del sitio web institucional.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Scraping estático | `requests` + `BeautifulSoup4` |
| Scraping dinámico | `Playwright` (Chromium headless) |
| PDFs | `pdfplumber` |
| Embeddings | `sentence-transformers` → `paraphrase-multilingual-MiniLM-L12-v2` (local) |
| Vector DB | `ChromaDB` (local, índice HNSW coseno) |
| LLM | `google-genai` → `gemini-3.1-flash-lite-preview` (con fallback) |
| Backend | `FastAPI` + `uvicorn` |
| Frontend | React + Vite + TypeScript + TailwindCSS |
| Bot adicional | Telegram (`python-telegram-bot`) |
| Contenedores | Docker Compose (3 servicios) |

---

## Arquitectura General

```
Usuario (Web / Telegram)
        │
        ▼
  ┌─────────────┐
  │  Frontend   │  React widget flotante embebido en página institucional
  │  (nginx:80) │
  └──────┬──────┘
         │ HTTP /chat
         ▼
  ┌─────────────────────────────────────────────────────┐
  │               Backend FastAPI (:8000)                │
  │  sanitize → classify_intent → [router / rewrite]    │
  │  → retrieve (RRF) → malla_lookup → generate         │
  └────────────────────┬────────────────────────────────┘
                       │
              ┌────────┴────────┐
              │   ChromaDB      │  Base de datos vectorial local
              │  (chroma_data)  │
              └─────────────────┘
```

---

## Pipeline RAG — Flujo Detallado

Cada consulta al endpoint `POST /chat` recorre estas etapas en orden:

### 1. Sanitización (`sanitizer.py`)
- Normalización Unicode NFC y eliminación de caracteres de control.
- Truncado a **500 caracteres** máximo.
- Detección de **prompt injection** (patrones en inglés y español) con logging de alertas.
- Neutralización de marcadores de sistema (`[INST]`, `<<SYS>>`, `<|im_start|>`, etc.).
- Validación de `session_id` (solo alfanuméricos/guiones, máx. 64 chars).

### 2. Clasificación de Intención (`intent.py`)
Clasificador **puramente heurístico (cero latencia LLM)** basado en expresiones regulares. Devuelve una de 5 intenciones:

| Intención | Descripción | Comportamiento |
|-----------|-------------|----------------|
| `conversational` | Meta-operación sobre respuesta anterior (resumir, ampliar, simplificar…) | Omite RAG, responde desde historial |
| `comparison` | Comparación explícita entre programas/servicios | Duplica `top_k` para cubrir ambos lados |
| `recommendation` | Solicitud de orientación personalizada | Activa hint de modo recomendación en el prompt |
| `followup` | Pregunta corta con contexto implícito (≤7 palabras o con deícticos) | Reescritura de query + clasificación en paralelo |
| `informational` | Consulta informativa estándar | Flujo RAG normal |

### 3. Reescritura de Followup (`pipeline.py → _rewrite_followup`)
Cuando la intención es `followup`, se reescribe la query corta en una consulta autocontenida usando los últimos **3 turnos de historial** y la clasificación de categoría se ejecutan en **paralelo** con `ThreadPoolExecutor`.

### 4. Clasificación de Categoría (`router.py`)
LLM multi-etiqueta que asigna hasta **3 categorías simultáneas**:

| Categoría | Temas cubiertos |
|-----------|-----------------|
| `admisiones` | Inscripción, requisitos, fechas, calendario académico |
| `programas` | Carreras, mallas, pensum, créditos, posgrados |
| `costos` | Matrícula, derechos pecuniarios, precios, pagos |
| `bienestar` | Servicios, prácticas, inglés, deportes, salud |
| `becas` | Financiamiento, apoyo socioeconómico, subsidios |
| `institucional` | Historia, acreditación, misión, visión |
| `general` | Cualquier otra pregunta |

Estrategia de fallback de modelos: `gemini-3.1-flash-lite-preview` → `gemini-2.5-flash` → `gemini-1.5-flash`.

### 5. Recuperación Híbrida (`retriever.py`)
Pipeline de recuperación con múltiples capas:

1. **Inyección de sinónimos**: expande "sistemas" → "ingeniería de software / desarrollo de software" antes de embedear.
2. **Embeddings locales**: codifica todas las variantes con `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers).
3. **Búsqueda dual**:
   - Con filtro de categoría en ChromaDB (para precisión temática).
   - Sin filtro (para capturar PDFs y documentos fuera de categoría estricta).
4. **RRF — Reciprocal Rank Fusion** (`k=60`): fusiona todos los rankings en una lista única, combinando hasta `n_queries × n_filtros × 2` listas de candidatos.
5. **Umbral de similitud coseno**: descarta chunks con score < `MIN_SCORE` (default `0.30`).

### 6. Lookup de Malla Curricular (`malla_lookup.py`)
Si la query contiene palabras clave de currículo (`malla`, `materia`, `semestre`, `pensum`, `crédito`, `curso`…):
- **`lookup_malla`**: búsqueda difusa (`difflib`) sobre nombres de programas en `mallas_curriculares.json`.
- **`lookup_course`**: búsqueda difusa por nombre de materia en todos los programas.
El resultado se inyecta como sección estructurada `## MALLA CURRICULAR ESTRUCTURADA` en el contexto del LLM.

### 7. Generación de Respuesta (`generator.py`)
- Construye el contexto a partir de chunks recuperados + malla estructurada.
- Inyecta un **hint de intención** en el prompt según el modo detectado (tabla comparativa, recomendación fundamentada, seguimiento coherente).
- Incluye historial de conversación sanitizado.
- Usa `SYSTEM_PROMPT` con **12 reglas** explícitas: fidelidad al contexto, honestidad sobre datos faltantes, prohibición de inventar fechas futuras, manejo de programas similares, seguridad contra injection en el prompt.
- Prompt especial `NO_INFO_PROMPT` cuando no hay contexto disponible: genera orientación contextualizada (no un mensaje genérico).
- Prompt `CONVERSATIONAL_PROMPT` para meta-operaciones sin RAG.
- Fallback de modelos: `gemini-3.1-flash-lite-preview` → `gemini-2.5-flash` → `gemini-1.5-flash`.
- Fallback de texto estático si todos los modelos fallan.

---

## Pipeline de Ingesta de Datos

### Scrapers

| Módulo | Tecnología | Uso |
|--------|-----------|-----|
| `static_scraper.py` | `requests` + BeautifulSoup4 | Páginas HTML simples; opcionalmente descubre y encola URLs de programas |
| `dynamic_scraper.py` | Playwright (Chromium headless) | JS-rendered: páginas de programas, calendarios académicos |
| `pdf_extractor.py` | `pdfplumber` | Extrae texto de PDFs enlazados desde las páginas |

**Estrategias especiales del scraper dinámico:**
- `follow_programs`: indexa el listado de programas y sigue cada link de programa individual.
- `follow_calendar`: detecta el semestre académico más reciente por año+número en los href y solo descarga ese calendario.
- Limpieza de DOM en JavaScript: elimina `<nav>`, `<footer>`, `<header>`, cookies banners y clases de ruido antes de extraer texto.
- Extrae PDFs embebidos (`<object>`, `<embed>`, `<iframe>`, `<a href="*.pdf">`).

### Limpieza y Chunking

- `cleaner.py`: normalización Unicode, eliminación de boilerplate institucional (breadcrumbs, links de RRSS, textos repetitivos), deduplicación de líneas, eliminación de URLs standalone.
- `chunker.py` — parámetros diferenciados por tipo de fuente:

| Tipo | `chunk_size` | `overlap` |
|------|-------------|---------|
| `web` | 400 chars | 80 chars |
| `pdf` | 700 chars | 120 chars |

Separadores jerárquicos: `\n\n` → `\n` → `. ` → ` ` → `""`.

### Indexación (ChromaDB)

- Modelo de embeddings local `paraphrase-multilingual-MiniLM-L12-v2`, batch size 32.
- Índice HNSW con métrica coseno.
- Metadata enriquecida por chunk: `url`, `categoria`, `tipo`, `chunk_index`, `titulo`, `program_name`, `level` (pregrado/posgrado), `source_type` (web_general, web_program, pdf), `program_slug`.

### Documentos Manuales

`manual_docs.json` permite agregar documentos curados que no están en el sitio web. Los documentos con texto que empiece por `TODO:` se omiten automáticamente (son placeholders).

### Uso del script de ingesta

```bash
# Primera vez (borra ChromaDB y regenera):
python run_ingestion.py --reset

# Actualización incremental:
python run_ingestion.py

# Solo scraping (genera raw_pages.json sin indexar):
python run_ingestion.py --scrape-only

# Solo indexar desde raw_pages.json existente:
python run_ingestion.py --index-only

# Combinar --index-only con --reset para reindexar desde raw existente:
python run_ingestion.py --index-only --reset
```

> **Nota:** El scraping completo puede tomar varios minutos por el uso de Playwright.

---

## Frontend

Widget de chat flotante embebido sobre la página web institucional (`UniversityPage.tsx`).

### Funcionalidades

- **Widget flotante**: botón con animación pulse, tooltip de bienvenida, panel de 520×680 px.
- **Modo pantalla completa**: toggle para expandir el chat a `100vw × 100vh`.
- **Responsive mobile**: se adapta automáticamente en pantallas < 480 px.
- **Sesión persistente**: `session_id` generado con `crypto.randomUUID()` y guardado en `localStorage`, sobrevive recargas de página.
- **Historial persistente**: mensajes guardados en `localStorage` y recuperados al reabrir.
- **Health check**: polling al endpoint `/health` con indicador de color en el header (verde / amarillo / rojo) y banner de advertencia si el backend está offline.
- **Wizard de orientación vocacional** (`useWizard.ts`): flujo guiado de **4 pasos** (área de interés → nivel → modalidad → disponibilidad horaria) que construye una query enriquecida para el pipeline RAG. Se activa:
  - Desde chip de bienvenida "Encuentra tu programa ideal".
  - Automáticamente si el usuario escribe frases como "no sé qué estudiar", "recomiéndame una carrera", etc.
- **Nueva conversación**: limpia mensajes, genera nuevo `session_id` y reinicia el wizard.
- **Manejo de errores tipados**: `ApiError` con códigos `network`, `timeout`, `validation`, `rate_limit`, `server` mapeados a mensajes amigables.
- **Renderizado de Markdown** en respuestas del bot (negritas, tablas, listas).
- **Lista de fuentes**: muestra los URLs de la información recuperada por el RAG.

### Categorías de sugerencias rápidas

La pantalla de bienvenida muestra chips de consultas frecuentes organizados en categorías: Programas, Admisiones, Costos, Bienestar y Wizard de orientación.

---

## API REST

| Método | Endpoint | Descripción |
|--------|---------|-------------|
| `POST` | `/chat` | Consulta al pipeline RAG. Cuerpo: `{query, session_id?}` |
| `GET` | `/health` | Estado del servicio |
| `GET` | `/categorias` | Lista de categorías disponibles |

**Respuesta de `/chat`:**
```json
{
  "respuesta": "...",
  "fuentes": ["https://..."],
  "categoria": "programas",
  "categorias": ["programas", "costos"],
  "intent": "comparison",
  "session_id": "abc123"
}
```

**Gestión de sesiones en memoria:**
- Máximo **10 mensajes** (5 turnos) por sesión.
- Máximo **1000 sesiones** activas simultáneas (protección contra memory flooding).
- Sesiones sin `session_id` se procesan sin historial.

---

## Bot de Telegram

`telegram_bot.py` conecta el bot de Telegram a la API REST usando el `chat_id` de Telegram como `session_id` (historial por conversación).

```bash
# Iniciar el bot (requiere TELEGRAM_BOT_TOKEN en .env)
python backend/telegram_bot.py
```

Comandos disponibles: `/start` (bienvenida). Cualquier otro mensaje se envía al pipeline RAG.

---

## Despliegue con Docker

```bash
# Construir e iniciar todos los servicios
docker compose up --build -d

# Ver logs
docker compose logs -f

# Detener
docker compose down
```

### Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `bravobot-backend` | interno :8000 | FastAPI, solo accesible desde nginx |
| `bravobot-frontend` | público :80 | nginx + build de Vite + reverse proxy a /chat |
| `bravobot-telegram` | — | Bot de Telegram como worker independiente |

- **Volumen persistente** `bravobot-chroma-data` para ChromaDB.
- **Health check** del backend cada 30 s; el frontend y el bot de Telegram esperan a que el backend esté saludable antes de arrancar.

---

## Instalación Local (sin Docker)

### Requisitos

- Python 3.11+
- Node.js 18+
- Cuenta de Google AI Studio con API key

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Editar .env y agregar GEMINI_API_KEY
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
# Editar .env: VITE_API_URL=http://localhost:8000
```

### Ejecución

```bash
# 1. Ingesta (primera vez)
python run_ingestion.py --reset

# 2. Backend
cd backend && uvicorn api.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm run dev
# → http://localhost:5173

# 4. (Opcional) Bot de Telegram
python backend/telegram_bot.py
```

Documentación interactiva de la API: http://localhost:8000/docs

---

## Estructura del Proyecto

```
BravoBot/
├── backend/
│   ├── scraper/
│   │   ├── urls.py              # URLs curadas con prioridad y metadata
│   │   ├── static_scraper.py   # Scraper requests + BeautifulSoup4
│   │   ├── dynamic_scraper.py  # Playwright: programas, calendarios, PDFs
│   │   └── pdf_extractor.py    # Extracción de texto de PDFs
│   ├── ingestion/
│   │   ├── cleaner.py          # Limpieza y deduplicación de texto
│   │   ├── chunker.py          # División en chunks (web/pdf)
│   │   └── embedder.py         # Embeddings locales + carga a ChromaDB
│   ├── rag/
│   │   ├── sanitizer.py        # Sanitización y anti-injection
│   │   ├── intent.py           # Clasificador de intención (heurístico)
│   │   ├── router.py           # Router LLM multi-categoría
│   │   ├── retriever.py        # Recuperación híbrida con RRF
│   │   ├── malla_lookup.py     # Lookup fuzzy de mallas curriculares
│   │   ├── generator.py        # Generación de respuesta con Gemini
│   │   └── pipeline.py         # Orquestador principal del pipeline
│   ├── api/
│   │   └── main.py             # FastAPI app, sesiones, endpoints
│   ├── data/
│   │   ├── mallas_curriculares.json  # Mallas estructuradas por programa
│   │   └── manual_docs.json          # Documentos curados manualmente
│   ├── telegram_bot.py         # Bot de Telegram
│   ├── requirements.txt
│   ├── requirements-ingestion.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── ChatWidget.tsx       # Widget flotante principal
│       │   ├── ChatWindow.tsx       # Ventana de mensajes + bienvenida
│       │   ├── MessageBubble.tsx    # Burbuja con Markdown + wizard options
│       │   ├── InputBar.tsx         # Barra de entrada
│       │   ├── SourcesList.tsx      # Lista de fuentes del RAG
│       │   └── UniversityPage.tsx   # Página institucional con widget
│       ├── hooks/
│       │   ├── useHealthCheck.ts    # Polling de estado del backend
│       │   └── useWizard.ts         # Wizard de orientación vocacional
│       └── services/
│           ├── api.ts               # Cliente HTTP (axios) con errores tipados
│           └── types.ts             # Tipos TypeScript de la API
├── docker-compose.yml
└── run_ingestion.py            # CLI de ingesta
```

---

## Variables de Entorno

### Backend (`backend/.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | API key de Google AI Studio | **requerido** |
| `COLLECTION_NAME` | Nombre de la colección ChromaDB | `bravobot` |
| `EMBEDDING_MODEL` | Modelo de sentence-transformers | `paraphrase-multilingual-MiniLM-L12-v2` |
| `TOP_K` | Chunks a recuperar por query | `8` |
| `MIN_SCORE` | Score coseno mínimo para incluir un chunk | `0.30` |
| `CHUNK_SIZE` | Tamaño de chunks en caracteres | `500` |
| `CHUNK_OVERLAP` | Overlap entre chunks | `50` |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | opcional |
| `API_URL` | URL del backend para el bot de Telegram | `http://localhost:8000/chat` |

### Frontend (`frontend/.env`)

| Variable | Descripción | Default |
|----------|-------------|---------|
| `VITE_API_URL` | URL base de la API (vacío en Docker, proxy nginx) | `""` |

---

## Seguridad

- **Prompt injection**: detección activa de patrones en inglés/español + neutralización de marcadores de sistema antes de cualquier llamada LLM.
- **Pydantic validation**: validación de tipo y longitud en el modelo `ChatRequest` antes de procesar.
- **session_id**: formato estricto (alfanumérico + guiones, máx. 64 chars), validado en dos capas (Pydantic + sanitizer).
- **Memory flooding**: límite de 1000 sesiones activas simultáneas; nuevas sesiones se rechazan con HTTP 429.
- **Rate limiting estructural**: historial de sesión limitado a 10 mensajes (5 turnos).
- **Prompt wrapping**: las queries de usuario se encierran en etiquetas `<PREGUNTA_ASPIRANTE>...</PREGUNTA_ASPIRANTE>` con instrucción explícita al LLM de ignorar instrucciones dentro de esas etiquetas.
- **CORS**: orígenes permitidos configurados explícitamente (`localhost:5173`, `localhost:3000`).
