# BravoBot — Evolución del Proyecto

Documento que rastrea los cambios arquitectónicos y de funcionalidades desde la propuesta inicial del hackathon hasta el estado actual del sistema.

---

## Punto de partida: Propuesta del Hackathon (`resumen-bravobot.md`)

El concepto original planteaba un RAG básico de **3 pasos lineales**:

```
Consulta → [Router: 1 categoría] → [Retrieval filtrado] → [Generación] → Respuesta
```

| Dimensión | Estado inicial |
|-----------|---------------|
| UI | **Streamlit** (prototipo rápido) |
| Embeddings | No especificados (dependencia de API externa) |
| Router | Una sola categoría por query |
| Retrieval | Búsqueda semántica simple filtrada por metadata |
| Conversación | Sin historial |
| Seguridad | Sin capa de protección |
| Datos estructurados | Sin soporte especial para mallas curriculares |
| Plataformas | Solo web (Streamlit) |
| Despliegue | Sin contenedores |
| Modelos LLM | `gemini-2.5-flash` (único) |

Las categorías iniciales incluían **noticias** (para evidenciar vigencia del contenido en el hackathon).

---

## Fase 1 — Pivote a producción (primera versión documentada en `README_old.md`)

### Cambios respecto a la propuesta

#### Frontend: Streamlit → React + Vite + TailwindCSS
**Razón:** Streamlit es suficiente para un prototipo de hackathon, pero no es embebible en una página web institucional existente. React permite construir un widget flotante que se integra sobre la web de Pascual Bravo sin reemplazarla.

#### Backend: FastAPI + uvicorn como API REST
**Razón:** Separar el backend del frontend con una API REST permite servir múltiples clientes (web, Telegram, futuras apps) sin cambiar la lógica del RAG.

#### Modularización del código
El código se organizó en módulos separados (`scraper/`, `ingestion/`, `rag/`, `api/`) en lugar de un script monolítico.

#### Embeddings: Google API (`text-embedding-004`)
En esta versión los embeddings se generaban mediante llamada a la API de Google, lo que sumaba latencia de red y costo por cada chunk durante la ingesta.

#### Estado de la ingesta en esta fase
- Chunking genérico (parámetros únicos para todos los tipos de documento).
- Sin soporte diferenciado para PDFs.
- Metadata básica: `url`, `categoria`.

#### Lo que aún NO existía
- Intent classifier
- Sanitizador de prompts
- Malla curricular estructurada
- Historial de conversación
- Multi-query expansion
- RRF
- Telegram bot
- Docker

---

## Fase 2 — Optimizaciones de latencia y seguridad

### 2.1 Embeddings: API de Google → `sentence-transformers` (local)

**Cambio:** `google-genai text-embedding-004` → `paraphrase-multilingual-MiniLM-L12-v2` corriendo localmente.

**Razones:**
- Elimina una llamada de red por cada query en tiempo de inferencia (reducción de latencia directa).
- Sin costo adicional por API en embeddings.
- El modelo MiniLM multilingüe cubre bien el español sin degradación notable de calidad.
- Permite uso offline y control total sobre el modelo de embeddings.

### 2.2 Router: una categoría → multi-categoría (hasta 3)

**Cambio:** El router pasó de retornar una etiqueta a retornar hasta 3 categorías separadas por `+`.

**Razones:** Preguntas reales de aspirantes frecuentemente cruzan categorías: *"¿Cuánto cuesta Mecatrónica y hay becas?"* requiere chunks de `costos` y `becas`. Con una sola categoría, la mitad de la pregunta quedaba sin contexto relevante.

### 2.3 Cadena de fallback de modelos

**Cambio:** Todo uso de LLM (router, retriever, pipeline, generator) pasó a usar la cadena `gemini-3.1-flash-lite-preview` → `gemini-2.5-flash` → `gemini-2.5-flash-lite`.

**Razones:**
- `gemini-3.1-flash-lite-preview` es el modelo más rápido y económico; se intenta primero.
- Si falla por rate limit (429) o error temporal (503), el sistema no se cae — degrada al siguiente modelo disponible.
- Elimina el punto único de fallo en cada componente LLM.

### 2.4 Sanitizador de prompts (`sanitizer.py`)

**Cambio:** Capa centralizada de sanitización aplicada a **toda** entrada de usuario antes de cualquier LLM.

**Razones:** Con un sistema público, los usuarios pueden intentar prompt injection para extraer el system prompt, cambiar el comportamiento del bot o usarlo como proxy para generar contenido fuera del dominio.

Medidas implementadas:
- Detección de ~20 patrones de injection en inglés y español.
- Neutralización de marcadores de sistema (`[INST]`, `<<SYS>>`, `<|im_start|>`, etc.).
- Truncado a 500 caracteres (previene ataques de contexto masivo).
- Eliminación de caracteres de control Unicode.
- Validación estricta del formato de `session_id`.

Adicionalmente, las queries se encierran en etiquetas XML (`<PREGUNTA_ASPIRANTE>`) con instrucción explícita al LLM de ignorar instrucciones dentro de ellas.

### 2.5 Chunking diferenciado por tipo de fuente

**Cambio:** Parámetros de chunking separados para `web` y `pdf`.

| Tipo | `chunk_size` | `overlap` |
|------|-------------|---------|
| `web` | 400 chars | 80 chars |
| `pdf` | 700 chars | 120 chars |

**Razones:** Los PDFs (calendarios académicos, aranceles) tienen párrafos más largos y densos con información numérica y tabular que no debe partirse en chunks pequeños. Los chunks más grandes preservan el contexto de una tabla completa.

### 2.6 Metadata enriquecida en ChromaDB

**Cambio:** Se agregaron campos `level` (pregrado/posgrado), `source_type` (web_general, web_program, pdf), `program_name`, `program_slug`.

**Razones:** Permite distinguir en el retrieval si un chunk proviene de una página de programa específico, de contenido general o de un PDF, facilitando búsquedas más precisas y trazabilidad de fuentes.

---

## Fase 3 — Inteligencia conversacional

### 3.1 Clasificador de intención heurístico (`intent.py`)

**Cambio:** Nuevo módulo que clasifica la intención de cada query **sin llamada LLM** (solo regex).

**Razones:** Añadir un LLM para clasificar intención hubiera sumado ~500–800ms de latencia extra por mensaje. Al usar expresiones regulares, la clasificación cuesta microsegundos. Las 5 intenciones cubren los patrones más comunes sin necesidad de un modelo:

| Intención | Por qué es necesaria |
|-----------|---------------------|
| `conversational` | "Resúmelo" no debe buscar en ChromaDB — solo operar sobre la respuesta anterior |
| `comparison` | Necesita el doble de contexto para cubrir ambos lados de la comparación |
| `recommendation` | Activa un prompt especializado que emite una opinión fundamentada |
| `followup` | Una query de ≤7 palabras como "¿y los costos?" carece de contexto sin historial — requiere reescritura |
| `informational` | Flujo RAG estándar |

### 3.2 Gestión de historial de conversación

**Cambio:** El endpoint `/chat` acepta un `session_id` y mantiene historial por sesión en memoria.

**Razones:** Sin historial, cada pregunta es independiente y el bot no puede responder correctamente a *"¿y esa carrera tiene posgrado?"*. El historial permite respuestas coherentes en conversaciones multi-turno.

Decisiones de diseño:
- **Máximo 10 mensajes (5 turnos)** por sesión: balance entre contexto útil y tamaño de prompt.
- **Máximo 1000 sesiones** simultáneas: previene agotamiento de memoria RAM en producción.
- Almacenamiento en memoria (no DB): simplicidad operativa para el alcance actual.

### 3.3 Reescritura de followup en paralelo (`pipeline.py`)

**Cambio:** Para intent `followup`, la reescritura de query y la clasificación de categoría se ejecutan en **paralelo** con `ThreadPoolExecutor`.

**Razones:** Ambas operaciones son independientes entre sí y cada una requiere una llamada LLM (~500ms). Ejecutarlas en paralelo reduce la latencia total a ~500ms en lugar de ~1000ms.

La reescritura usa los últimos 3 turnos de historial para construir una query autocontenida. Ejemplo: *"¿y los requisitos?"* → *"¿Cuáles son los requisitos de admisión para Ingeniería de Software en Pascual Bravo?"*

---

## Fase 4 — Mejoras de retrieval

### 4.1 Multi-query expansion (`retriever.py → expand_query`)

**Cambio:** Se genera 2 reformulaciones alternativas de la query con LLM antes de embedear.

**Razones:** Una sola formulación puede no capturar todos los chunks relevantes. Si el usuario pregunta *"¿cuánto vale el semestre?"* y los chunks dicen *"derechos pecuniarios"*, la distancia semántica puede ser suficiente pero el matching léxico ayuda. Con 3 variantes (original + 2 reformulaciones), la cobertura mejora significativamente.

### 4.2 Búsqueda dual (con y sin filtro de categoría)

**Cambio:** Cada embedding se consulta dos veces: con filtro de categoría y sin filtro.

**Razones:** Los PDFs (calendarios, aranceles) no siempre tienen la categoría perfectamente asignada. La búsqueda sin filtro actúa como red de seguridad para capturar documentos relevantes que el router no clasificó exactamente en la categoría esperada.

### 4.3 Reciprocal Rank Fusion — RRF (`k=60`)

**Cambio:** Reemplazó la selección simple del mejor score coseno por fusión de múltiples listas de ranking.

**Razones:** Con múltiples queries y múltiples filtros, se generan varias listas de candidatos potencialmente solapadas. RRF combina los rankings de forma robusta sin sesgar hacia ninguna métrica individual: un chunk que aparece consistentemente en el top-10 de varias listas obtiene mayor score final que uno que lidera solo una lista.

### 4.4 Umbral mínimo de score coseno (`MIN_SCORE = 0.30`)

**Cambio:** Los chunks con similitud coseno < 0.30 se descartan aunque hayan pasado el RRF.

**Razones:** RRF puede promover chunks que aparecen en muchas listas pero con score coseno bajo. El umbral garantiza que solo se inyecta contexto genuinamente relevante al LLM, reduciendo el ruido que podría confundir la generación.

### 4.5 Inyección de sinónimos

**Cambio:** Si la query contiene "sistemas" sin "software", se agrega automáticamente "ingeniería de software desarrollo de software" a la query de búsqueda.

**Razones:** La institución no tiene "Ingeniería de Sistemas" como programa (término muy común en Colombia). El programa real es "Ingeniería de Software". Sin esta corrección, las consultas más frecuentes de los aspirantes no encontrarían nada relevante.

### 4.6 TOP_K: 5 → 8

**Cambio:** El número de chunks recuperados por query subió de 5 a 8.

**Razones:** Al usar búsqueda dual (con y sin filtro) y RRF, el conjunto inicial de candidatos es mucho más amplio. TOP_K=5 resultaba insuficiente para capturar toda la información necesaria cuando la query abarca múltiples temas. TOP_K=8 compensa sin incrementar el contexto del LLM de forma excesiva.

---

## Fase 5 — Datos estructurados (mallas curriculares)

### 5.1 `malla_lookup.py` + `mallas_curriculares.json`

**Cambio:** Para preguntas sobre materias, semestres o créditos, el sistema consulta directamente un JSON estructurado con las mallas curriculares en lugar de (o además de) los chunks vectoriales.

**Razones:** El RAG vectorial no es el enfoque ideal para datos tabulares estructurados. Los chunks de texto extraídos de las páginas de programas pueden romper una tabla de materias en fragmentos poco útiles. Con el JSON estructurado:
- La respuesta sobre "¿qué materias tiene el semestre 3 de Electrónica?" es exacta y completa.
- El LLM recibe la información como sección `## MALLA CURRICULAR ESTRUCTURADA` organizada semestre por semestre.
- La búsqueda usa `difflib` para tolerancia a errores ortográficos en nombres de programas y materias.

---

## Fase 6 — Generación avanzada

### 6.1 Prompts especializados por intención

**Cambio:** En lugar de un único system prompt, el generador tiene 3 prompts y 4 modos:

| Prompt | Cuándo se usa |
|--------|--------------|
| `SYSTEM_PROMPT` | Consultas informativas, comparaciones, recomendaciones, followups |
| `CONVERSATIONAL_PROMPT` | Meta-operaciones sobre la respuesta anterior (resumir, ampliar, etc.) |
| `NO_INFO_PROMPT` | Cuando no hay contexto RAG disponible |

**Razones:** Un prompt genérico no produce el mismo resultado que uno especializado. Para una comparación, se instruye al modelo a usar tablas comparativas. Para una recomendación, se le permite emitir una opinión fundamentada. Para el modo conversacional, se le pide operar únicamente sobre el historial sin inventar información nueva.

### 6.2 12 reglas explícitas en el system prompt

**Razones (selección de las más importantes):**
- **Regla anti-alucinación de fechas futuras**: las fechas académicas cambian cada año; proyectar el calendario actual hacia "el próximo año" generaba respuestas incorrectas con alta confianza.
- **Regla de programas similares**: si el usuario pregunta por "Ingeniería de Sistemas" y el contexto tiene "Ingeniería de Software", el bot debe informar amablemente que ese es el programa equivalente.
- **NO_INFO no genérico**: en lugar de responder siempre *"consulta en la página web"*, el bot debe nombrar el tema específico y orientar al canal correcto (admisiones, bienestar, registro y control, etc.) según de qué se trate.

### 6.3 Fallback de texto estático

**Razones:** Si la cadena completa de modelos (3 modelos) falla, el sistema retorna un mensaje predefinido en lugar de un error HTTP 500. El usuario recibe orientación mínima en lugar de una pantalla de error.

---

## Fase 7 — Nuevas plataformas y despliegue

### 7.1 Bot de Telegram (`telegram_bot.py`)

**Cambio:** Nuevo cliente que conecta Telegram al endpoint `/chat`, usando el `chat_id` de Telegram como `session_id`.

**Razones:** Ampliar el alcance del asistente a Telegram sin duplicar la lógica del RAG. El bot reutiliza completamente el pipeline existente; solo actúa como proxy HTTP.

### 7.2 Docker Compose (3 servicios)

**Cambio:** Contenerización completa con `backend`, `frontend` (nginx) y `telegram-bot` como servicios independientes.

**Razones:**
- Reproducibilidad: cualquier máquina con Docker levanta el sistema completo con un solo comando.
- Aislamiento: el backend no expone puertos al host; nginx actúa como único punto de entrada público.
- El volumen `bravobot-chroma-data` persiste ChromaDB entre reinicios sin intervención manual.
- Health check automático: el frontend y el bot solo arrancan cuando el backend confirma estar listo (evita errores en arranque frío mientras ChromaDB carga).

### 7.3 Frontend embebido en página institucional (`UniversityPage.tsx`)

**Cambio:** El chat ya no es la página completa sino un widget flotante sobre una vista de la web institucional.

**Razones:** La integración real en el sitio de Pascual Bravo requiere que el chatbot coexista con el contenido existente, no que lo reemplace. El widget flotante con botón pulsante en esquina inferior derecha sigue el patrón UX estándar de chatbots institucionales.

---

## Fase 8 — UX del Frontend

### 8.1 Wizard de orientación vocacional (`useWizard.ts`)

**Cambio:** Flujo guiado de 4 preguntas (área → nivel → modalidad → disponibilidad) que construye una query enriquecida para el RAG.

**Razones:** Muchos aspirantes no saben cómo formular su pregunta o no conocen los nombres exactos de los programas. El wizard elimina esa fricción: el usuario elige opciones en lugar de escribir, y el sistema construye una query de recomendación completa y bien formateada.

Se activa automáticamente al detectar frases como *"no sé qué estudiar"* o *"recomiéndame una carrera"*, o manualmente desde un chip en la pantalla de bienvenida.

### 8.2 Sesión persistente en `localStorage`

**Razones:** Sin persistencia, cerrar el chat o recargar la página borra el historial y genera un nuevo `session_id`, perdiendo el contexto de la conversación. Con `localStorage`, el historial y la sesión sobreviven recargas.

### 8.3 Health check y banner offline

**Razones:** Si el backend no está disponible, el usuario debe saberlo inmediatamente (y no confundirse pensando que el bot no entiende sus preguntas). El indicador de color (verde/amarillo/rojo) y el banner rojo informan el estado en tiempo real.

### 8.4 Manejo de errores tipados (`ApiError`)

**Razones:** `axios` devuelve errores con diferentes estructuras según el tipo de fallo (red, timeout, 422, 429, 500). Mapear cada código a un mensaje en español claro para el usuario mejora la experiencia cuando algo falla.

---

## Resumen de la evolución

```
Hackathon proposal          Primera versión              Estado actual
────────────────────        ─────────────────            ─────────────
Streamlit UI           →    React widget            →    Widget flotante + UniversityPage
                                                          + Wizard + Fullscreen + Mobile
                                                          + Health check + localStorage

1 categoría/query      →    Multi-categoría (3)     →    Multi-categoría + Intent classifier
                                                          (5 intenciones, cero latencia LLM)

Google API embeddings  →    Google API embeddings   →    sentence-transformers LOCAL
                                                          (sin latencia de red, sin costo)

Simple ChromaDB query  →    ChromaDB + filtro       →    Dual search + Multi-query expansion
                                                          + RRF fusion + MIN_SCORE threshold
                                                          + synonym injection + TOP_K=8

Sin historial          →    Sin historial           →    Historial multi-turno por sesión
                                                          + followup rewrite en paralelo

Sin seguridad          →    Sin seguridad           →    sanitizer.py (injection detection,
                                                          marcadores sistema, truncado)
                                                          + session flooding protection

Sin datos estructurados →   Sin datos estructurados →    malla_lookup.py + JSON estructurado
                                                          + fuzzy search con difflib

1 prompt genérico      →    1 prompt genérico       →    3 prompts + 4 modos de intención
                                                          + 12 reglas explícitas + fallback
                                                          chain (3 modelos)

Solo web               →    Solo web                →    Web + Telegram bot

Sin contenedores       →    Sin contenedores        →    Docker Compose (3 servicios)
                                                          + nginx reverse proxy
                                                          + ChromaDB volume + health check
```

---