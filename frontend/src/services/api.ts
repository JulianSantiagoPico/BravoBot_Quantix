// ─────────────────────────────────────────────────────────────────────────────
// BravoBot API Service
//
// Centraliza toda la comunicación HTTP con el backend FastAPI.
// En Docker, VITE_API_URL es vacío y nginx maneja el proxy.
// En dev local, VITE_API_URL = http://localhost:8000
// ─────────────────────────────────────────────────────────────────────────────

import axios, { AxiosError } from 'axios'
import type { ChatRequest, ChatResponse, HealthResponse, CategoriasResponse } from './types'

// Base URL: vacía en Docker (mismo origen via nginx), o URL explícita en dev
const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

const client = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000, // 30 s — el pipeline RAG puede tardar
})

// ── Tipos de error estructurados ─────────────────────────────────────────────

export type ApiErrorCode = 'network' | 'timeout' | 'validation' | 'rate_limit' | 'server' | 'unknown'

export interface ApiError {
  code: ApiErrorCode
  message: string
  status?: number
}

function parseError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const axiosErr = err as AxiosError<{ detail?: string }>
    if (!axiosErr.response) {
      if (axiosErr.code === 'ECONNABORTED') return { code: 'timeout', message: 'El servidor tardó demasiado. Intenta de nuevo.' }
      return { code: 'network', message: 'Sin conexión con el servidor. Verifica que el backend esté activo.' }
    }
    const status = axiosErr.response.status
    const detail = axiosErr.response.data?.detail ?? ''
    if (status === 422) return { code: 'validation', message: 'Tu pregunta no pudo procesarse. Verifica el texto ingresado.', status }
    if (status === 429) return { code: 'rate_limit', message: 'Demasiadas solicitudes activas. Espera un momento e intenta de nuevo.', status }
    if (status >= 500) return { code: 'server', message: `Error interno del servidor${detail ? ': ' + detail : ''}. Intenta más tarde.`, status }
    return { code: 'unknown', message: detail || 'Error desconocido.', status }
  }
  return { code: 'unknown', message: 'Error inesperado.' }
}

// ── Endpoints ─────────────────────────────────────────────────────────────────

/**
 * Envía una pregunta al pipeline RAG del backend.
 * @param query   Texto de la pregunta del usuario
 * @param sessionId ID de sesión para mantener contexto conversacional
 */
export async function sendMessage(query: string, sessionId?: string): Promise<ChatResponse> {
  const payload: ChatRequest = { query }
  if (sessionId) payload.session_id = sessionId
  try {
    const { data } = await client.post<ChatResponse>('/chat', payload)
    return data
  } catch (err) {
    throw parseError(err)
  }
}

/**
 * Verifica el estado del backend.
 * @returns HealthResponse o lanza ApiError
 */
export async function getHealth(): Promise<HealthResponse> {
  try {
    const { data } = await client.get<HealthResponse>('/health')
    return data
  } catch (err) {
    throw parseError(err)
  }
}

/**
 * Obtiene las categorías disponibles en el RAG.
 */
export async function getCategorias(): Promise<CategoriasResponse> {
  try {
    const { data } = await client.get<CategoriasResponse>('/categorias')
    return data
  } catch (err) {
    throw parseError(err)
  }
}
