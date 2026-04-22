// ─────────────────────────────────────────────────────────────────────────────
// BravoBot API — Tipos compartidos
// Refleja exactamente los modelos Pydantic de backend/api/main.py
// ─────────────────────────────────────────────────────────────────────────────

/** Payload enviado al endpoint POST /chat */
export interface ChatRequest {
  query: string
  session_id?: string
}

/** Respuesta del endpoint POST /chat */
export interface ChatResponse {
  respuesta: string
  fuentes: string[]
  categoria: string
  categorias: string[]
  session_id?: string
}

/** Respuesta del endpoint GET /health */
export interface HealthResponse {
  status: string
  service: string
}

/** Respuesta del endpoint GET /categorias */
export interface CategoriasResponse {
  categorias: string[]
}

/** Objeto de mensaje usado internamente en el widget */
export interface Message {
  id: string
  role: 'user' | 'bot'
  content: string
  fuentes?: string[]
  categoria?: string
}
