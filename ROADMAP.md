# BravoBot — Roadmap de Mejoras Futuras

Mejoras identificadas a partir del estado actual del sistema, organizadas por impacto y complejidad de implementación.

---

## Prioridad Alta — Confiabilidad y Experiencia Core

### 1. Streaming de respuestas (SSE)

**Problema actual:** El usuario espera en silencio hasta que el LLM termina de generar toda la respuesta (puede tardar 3–8 segundos). Esto genera la percepción de que el bot está colgado.

**Propuesta:**
- Endpoint `POST /chat/stream` con `StreamingResponse` (ya está en el roadmap arquitectónico).
- El frontend consume el stream con `EventSource` o `fetch` + `ReadableStream` y va renderizando token a token.
- El bot de Telegram no necesita cambios (usa `/chat` síncrono).

**Impacto:** Mejora drástica en percepción de velocidad sin cambiar la latencia real del LLM.

---

### 2. Persistencia de sesiones (Redis o SQLite)

**Problema actual:** El historial de conversaciones vive en memoria RAM del proceso. Cualquier reinicio del backend (deploy, crash, Docker restart) borra todas las sesiones activas.

**Propuesta:**
- Opción A (simple): SQLite con tabla `sessions(session_id, messages_json, updated_at)`.
- Opción B (escalable): Redis con TTL automático de 24 horas por sesión.
- Migrar `sessions: dict` en `main.py` a una capa de abstracción `SessionStore`.

**Impacto:** Los aspirantes no pierden el contexto de la conversación ante reinicios. Permite también analítica histórica.

---

### 3. Re-ingesta automática programada

**Problema actual:** La ingesta es un proceso manual (`python run_ingestion.py`). Si la institución actualiza costos, fechas o programas, el bot sigue respondiendo con datos viejos indefinidamente.

**Propuesta:**
- Scheduler semanal (APScheduler o cron en Docker) que ejecuta `run_ingestion.py` en modo incremental.
- Detector de cambios: comparar hash del contenido scrapeado contra el anterior; solo re-indexar páginas modificadas.
- Notificación por log (y opcionalmente Telegram/email al admin) cuando se detectan cambios en páginas críticas (costos, calendario académico).

**Impacto:** Garantiza que el bot siempre tenga información vigente sin intervención manual.

---

### 4. Caché de respuestas para queries frecuentes

**Problema actual:** Preguntas idénticas o muy similares (ej. "¿cuándo son las inscripciones?") ejecutan el pipeline completo (2–3 llamadas LLM) cada vez.

**Propuesta:**
- Caché semántico: al recibir una query, embedearla y comparar contra un índice de queries previas. Si la similitud coseno supera 0.92, retornar la respuesta cacheada.
- TTL de 12–24 horas (las respuestas institucionales no cambian intra-día).
- Implementación: dict en memoria o Redis con expiración.

**Impacto:** Reducción de latencia a ~50ms para el ~30–40% de queries repetitivas + ahorro de llamadas LLM.

---

### 5. Suite de tests automatizados

**Problema actual:** No existe ningún test automatizado. Cambios en el pipeline pueden romper funcionalidad existente sin detección inmediata.

**Propuesta:**
- `pytest` con fixtures para el pipeline RAG.
- Tests unitarios: `sanitize_query`, `classify_intent`, `_rrf_fuse`, `lookup_malla`, `lookup_course`.
- Tests de integración: `ask()` con mocks de ChromaDB y LLM.
- Tests de regresión para prompt injection: batería de inputs maliciosos que deben ser sanitizados correctamente.
- CI/CD: GitHub Actions que ejecuta los tests en cada push.

**Impacto:** Permite iterar con confianza sobre el pipeline sin romper comportamientos existentes.

---

## Prioridad Media — Calidad de Respuestas

### 6. Re-ranking con cross-encoder

**Problema actual:** RRF fusiona rankings de múltiples listas pero no evalúa la relevancia semántica directa entre la query y cada chunk.

**Propuesta:**
- Después del RRF, aplicar un cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2` o versión multilingüe) que re-puntúa los top-`2×K` candidatos.
- Retener los top-K con mejor score del cross-encoder.
- Ejecutar en el mismo proceso (modelo local, ~30ms adicionales).

**Impacto:** Mejora la relevancia final de los chunks enviados al LLM, especialmente en preguntas ambiguas.

---

### 7. Guardrails de salida del LLM

**Problema actual:** Solo se valida la entrada del usuario, pero la salida del LLM no se verifica. En casos edge, el modelo podría generar contenido fuera del dominio.

**Propuesta:**
- Post-procesador de respuesta que verifique:
  - La respuesta no contiene URLs inventadas (no del dominio `pascualbravo.edu.co`).
  - La respuesta no menciona nombres de programas que no existen en `mallas_curriculares.json`.
  - Longitud mínima: si la respuesta tiene < 20 caracteres, probablemente es un error de generación.
- Si falla la verificación, reintentar con temperatura más baja o retornar `NO_INFO_FALLBACK`.

---

### 8. Feedback loop del usuario

**Problema actual:** No existe mecanismo para saber qué respuestas fueron útiles y cuáles no.

**Propuesta:**
- Botones de 👍 / 👎 debajo de cada respuesta del bot en el frontend.
- Endpoint `POST /feedback` que almacena `{session_id, message_id, rating, query, respuesta}`.
- Dashboard simple (o export CSV) para revisar las respuestas mal valoradas.
- Usar las queries mal valoradas para enriquecer `manual_docs.json` con información faltante.

**Impacto:** Ciclo de mejora continua basado en datos reales de uso.

---

### 9. Expansión del corpus con documentos adicionales

**Problema actual:** El corpus cubre las URLs más críticas pero hay información relevante no indexada: reglamento estudiantil, tarifas de servicios específicos, convocatorias de becas externas, etc.

**Propuesta:**
- Ampliar `urls.py` con páginas secundarias del sitio.
- Mejorar `manual_docs.json` con documentos que no tienen URL pública (reglamentos en PDF internos).
- Añadir soporte para Google Sites (bienestar universitario ya tiene una URL de Google Sites — verificar si el scraper la cubre completamente).

---

### 10. Detección de idioma y soporte bilingüe

**Problema actual:** El sistema asume español. Si un usuario escribe en inglés (aspirante internacional o intercambio), la respuesta puede degradarse.

**Propuesta:**
- Detectar idioma de la query con `langdetect` (< 1ms).
- Si es inglés: traducir la query al español antes del embedding, generar respuesta en español y opcionalmente traducirla al inglés.
- Agregar instrucción al `SYSTEM_PROMPT` para responder en el idioma del usuario.

---

## Prioridad Media — Nuevas Plataformas

### 11. WhatsApp Business (Meta Cloud API)

**Contexto:** WhatsApp es el canal de mensajería dominante en Colombia. Un bot de WhatsApp alcanzaría a la mayoría de aspirantes sin que descarguen nada.

**Propuesta:**
- Webhook FastAPI para recibir mensajes de WhatsApp Business Cloud API.
- Reutilizar completamente el pipeline RAG existente (igual que el bot de Telegram).
- Usar el número de teléfono como `session_id`.
- Limitación: WhatsApp tiene restricciones en longitud de mensaje — implementar truncado inteligente de respuestas largas.

---

### 12. Widget embebible como script externo

**Problema actual:** El widget de chat está acoplado al build de React del proyecto. Para integrarlo en el sitio real de Pascual Bravo (que probablemente usa WordPress u otro CMS) habría que modificar el sitio institucional directamente.

**Propuesta:**
- Compilar el `ChatWidget` como un Web Component o un bundle JS standalone (`widget.js`).
- El sitio institucional lo integra con una sola línea: `<script src="https://bravobot.pascualbravo.edu.co/widget.js"></script>`.
- Sin dependencias de React ni del build del sitio huésped.

---

## Prioridad Baja — Escalabilidad y Operaciones

### 13. Rate limiting por IP / API key

**Problema actual:** La única protección contra abuso es el límite de sesiones (1000 simultáneas). Un actor malicioso podría hacer miles de requests sin `session_id` y saturar el LLM.

**Propuesta:**
- Middleware de rate limiting en FastAPI (`slowapi` o implementación custom).
- Límite sugerido: 20 requests/minuto por IP, 200/hora.
- Las IPs de la institución (red interna de Pascual Bravo) podrían tener límites más altos.

---

### 14. Dashboard de analítica

**Propuesta:**
- Logging estructurado (JSON) de cada request: `{timestamp, session_id, intent, categorias, query_length, response_time_ms, chunks_retrieved, model_used}`.
- Agregaciones útiles:
  - Temas más consultados por categoría.
  - Tasa de uso del wizard.
  - Distribución de intenciones detectadas.
  - Latencia promedio por modelo de fallback.
  - Queries que llegan a `NO_INFO_FALLBACK` (gaps de información).
- Stack simple: logs → archivo JSON → Grafana + Loki, o simplemente export a Google Sheets.

---

### 15. Autenticación para operaciones administrativas

**Problema actual:** Los endpoints de la API no tienen autenticación. En producción, operaciones como `/chat` deberían tener al menos un control básico.

**Propuesta:**
- API key simple en header `X-API-Key` para el endpoint `/chat` (generada por la institución, incluida en el frontend y el bot de Telegram).
- Previene uso no autorizado de la API desde fuera de los clientes oficiales.

---

### 16. Separar dependencias de ingesta y runtime

**Problema actual:** `requirements.txt` incluye `playwright` y `pdfplumber` que solo se necesitan en la ingesta, no en el servidor de producción. Esto infla la imagen Docker del backend.

**Propuesta:**
- Mantener `requirements.txt` para runtime del servidor (FastAPI, ChromaDB, sentence-transformers, google-genai).
- Mantener `requirements-ingestion.txt` solo para la ingesta (ya existe en el repo).
- Dockerfile separado para el worker de ingesta, o instrucción de instalar ingestion-deps solo cuando se corre la ingesta.

**Impacto:** Imagen Docker del backend más liviana (~40% menos) → arranque más rápido.

---

### 17. ChromaDB remoto / base vectorial administrada

**Problema actual:** ChromaDB corre local dentro del contenedor. Escalar horizontalmente (múltiples instancias del backend) requeriría sincronizar el volumen, lo cual es complejo.

**Propuesta (cuando el tráfico lo justifique):**
- Migrar a ChromaDB en modo servidor (`chromadb.HttpClient`) o a Qdrant Cloud / Weaviate Cloud.
- El backend pasa a ser stateless → permite múltiples réplicas sin coordinación de volúmenes.
- Pre-requisito: el volumen de consultas debe justificar la complejidad adicional.

---

## Resumen de Prioridades

| # | Mejora | Impacto | Complejidad |
|---|--------|---------|-------------|
| 1 | Streaming SSE | Alto | Baja |
| 2 | Persistencia de sesiones | Alto | Media |
| 3 | Re-ingesta automática | Alto | Media |
| 4 | Caché semántico | Alto | Media |
| 5 | Suite de tests | Alto | Media |
| 6 | Cross-encoder re-ranking | Medio | Media |
| 7 | Guardrails de salida | Medio | Baja |
| 8 | Feedback loop (👍/👎) | Medio | Baja |
| 9 | Expansión de corpus | Medio | Baja |
| 10 | Soporte bilingüe | Bajo | Baja |
| 11 | WhatsApp Business | Alto | Alta |
| 12 | Widget como script externo | Alto | Alta |
| 13 | Rate limiting por IP | Medio | Baja |
| 14 | Dashboard de analítica | Medio | Media |
| 15 | Autenticación API key | Medio | Baja |
| 16 | Separación de dependencias | Bajo | Baja |
| 17 | ChromaDB remoto | Bajo | Alta |
