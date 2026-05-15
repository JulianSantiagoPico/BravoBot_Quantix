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
  intent?: string
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

/** Opción de respuesta rápida del wizard de orientación */
export interface WizardOption {
  icon: string
  label: string
  value: string
}

/** Objeto de mensaje usado internamente en el widget */
export interface Message {
  id: string
  role: 'user' | 'bot'
  content: string
  fuentes?: string[]
  categoria?: string
  intent?: string
  wizardOptions?: WizardOption[]
}

/** Payload para POST /feedback/message — voto 👍/👎 por mensaje */
export interface MessageFeedbackPayload {
  session_id: string
  message_id: string
  rating: 1 | -1
  query?: string
  respuesta?: string
  categoria?: string
  intent?: string
}

/** Payload para POST /feedback/session — calificación 1–5 ⭐ al cerrar */
export interface SessionFeedbackPayload {
  session_id: string
  rating: number        // 1-5
  comment?: string
  n_messages: number
  n_bot_messages: number
  categorias: string[]
}
