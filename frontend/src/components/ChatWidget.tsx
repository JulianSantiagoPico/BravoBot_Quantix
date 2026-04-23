import { useState, useRef, useEffect } from 'react'
import ChatWindow from './ChatWindow'
import InputBar from './InputBar'
import { Message } from './MessageBubble'
import { sendMessage as apiSendMessage } from '../services/api'
import type { ApiError } from '../services/api'
import { useHealthCheck } from '../hooks/useHealthCheck'
import { useWizard, WIZARD_STEPS, buildWizardQuery, WIZARD_TRIGGER_PATTERNS } from '../hooks/useWizard'

// ── Constantes ──────────────────────────────────────────────────────────────
const SESSION_KEY = 'bravobot_session_id'
const MESSAGES_KEY = 'bravobot_messages'

let msgCounter = 0
function nextId() {
  return `msg-${++msgCounter}`
}

/** Genera o recupera el session_id persistente en localStorage */
function getOrCreateSessionId(): string {
  const stored = localStorage.getItem(SESSION_KEY)
  if (stored) return stored
  const newId = crypto.randomUUID().replace(/-/g, '').slice(0, 32)
  localStorage.setItem(SESSION_KEY, newId)
  return newId
}

/** Carga el historial de mensajes persistido */
function loadMessages(): Message[] {
  try {
    const raw = localStorage.getItem(MESSAGES_KEY)
    return raw ? (JSON.parse(raw) as Message[]) : []
  } catch {
    return []
  }
}

/** Persiste el historial de mensajes */
function saveMessages(msgs: Message[]) {
  try {
    localStorage.setItem(MESSAGES_KEY, JSON.stringify(msgs))
  } catch {
    // localStorage lleno o bloqueado — ignorar silenciosamente
  }
}

/** Traduce un ApiError a texto amigable para el usuario */
function errorText(err: ApiError): string {
  switch (err.code) {
    case 'network':    return 'Sin conexión con el servidor. Verifica que el backend esté activo.'
    case 'timeout':    return 'El servidor tardó demasiado en responder. Intenta de nuevo.'
    case 'validation': return 'Tu pregunta no pudo procesarse. Verifica el texto ingresado.'
    case 'rate_limit': return 'Demasiadas solicitudes activas. Espera un momento e intenta de nuevo.'
    case 'server':     return err.message
    default:           return 'Ocurrió un error inesperado. Por favor intenta de nuevo o visita pascualbravo.edu.co.'
  }
}

/* ── Close icon ── */
function CloseIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  )
}

function shouldStartWizard(text: string): boolean {
  return WIZARD_TRIGGER_PATTERNS.some((p) => p.test(text))
}

/* ── Fullscreen icon ── */
function FullscreenIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M8 21H5a2 2 0 0 0-2-2v-3M21 16v3a2 2 0 0 0-2 2h-3" />
    </svg>
  )
}

/* ── Restore icon ── */
function RestoreIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M3 21l7-7" />
    </svg>
  )
}

export default function ChatWidget() {
  const [isOpen, setIsOpen]         = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [messages, setMessages]     = useState<Message[]>(loadMessages)
  const [isLoading, setIsLoading]   = useState(false)

  // session_id persistente en localStorage — sobrevive recargas
  const sessionIdRef = useRef<string>(getOrCreateSessionId())

  // Health check al montar el componente
  const backendStatus = useHealthCheck()

  // Wizard de orientación
  const wizard = useWizard()

  // Persistir mensajes cada vez que cambian
  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  /** Envía la query al backend y añade la respuesta del bot. No añade mensaje de usuario. */
  const sendToBackend = async (query: string) => {
    setIsLoading(true)
    try {
      const data = await apiSendMessage(query, sessionIdRef.current)
      if (data.session_id && data.session_id !== sessionIdRef.current) {
        sessionIdRef.current = data.session_id
        localStorage.setItem(SESSION_KEY, data.session_id)
      }
      const botMsg: Message = {
        id: nextId(),
        role: 'bot',
        content: data.respuesta,
        fuentes: data.fuentes,
        categoria: data.categoria,
        intent: data.intent,
      }
      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      const errorMsg: Message = {
        id: nextId(),
        role: 'bot',
        content: errorText(err as ApiError),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsLoading(false)
    }
  }

  /** Maneja la respuesta del usuario a una pregunta del wizard */
  const handleWizardAnswer = (value: string) => {
    const userMsg: Message = { id: nextId(), role: 'user', content: value }
    const { nextStep, nextAnswers } = wizard.answerStep(value)

    if (nextStep === 0) {
      // Todas las preguntas respondidas — construir query y enviar al backend
      const query = buildWizardQuery(nextAnswers)
      setMessages((prev) => [...prev, userMsg])
      sendToBackend(query)
    } else {
      // Mostrar la siguiente pregunta del wizard
      const nextStepDef = WIZARD_STEPS[nextStep - 1]
      const botMsg: Message = {
        id: nextId(),
        role: 'bot',
        content: nextStepDef.question,
        wizardOptions: nextStepDef.options,
        intent: 'wizard',
      }
      setMessages((prev) => [...prev, userMsg, botMsg])
    }
  }

  /** Inicia el wizard desde el chip de la pantalla de bienvenida */
  const handleWizardStart = () => {
    if (isLoading) return
    const firstStep = WIZARD_STEPS[0]
    const introMsg: Message = {
      id: nextId(),
      role: 'bot',
      content:
        '¡Perfecto! Voy a ayudarte a encontrar el programa ideal para ti. ' +
        'Solo necesito que respondas **4 preguntas rápidas** 🎯\n\n' +
        firstStep.question,
      wizardOptions: firstStep.options,
      intent: 'wizard',
    }
    wizard.startWizard()
    setMessages((prev) => [...prev, introMsg])
  }

  const sendMessage = async (text: string) => {
    // Ruta 1: wizard activo — procesar como respuesta al wizard
    if (wizard.isActive) {
      handleWizardAnswer(text)
      return
    }

    // Ruta 2: frase de orientación detectada — iniciar wizard
    if (shouldStartWizard(text)) {
      const userMsg: Message = { id: nextId(), role: 'user', content: text }
      const firstStep = WIZARD_STEPS[0]
      const botMsg: Message = {
        id: nextId(),
        role: 'bot',
        content:
          '¡Claro! Voy a ayudarte a encontrar el programa ideal. ' +
          'Te haré **4 preguntas rápidas** para personalizar mi recomendación 🎯\n\n' +
          firstStep.question,
        wizardOptions: firstStep.options,
        intent: 'wizard',
      }
      wizard.startWizard()
      setMessages((prev) => [...prev, userMsg, botMsg])
      return
    }

    // Ruta 3: consulta normal al pipeline RAG
    const userMsg: Message = { id: nextId(), role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    await sendToBackend(text)
  }

  const handleSuggestion = (text: string) => {
    if (isLoading) return
    sendMessage(text)
  }

  /** Nueva conversación: limpia mensajes, reinicia session_id y wizard */
  const handleNewConversation = () => {
    setMessages([])
    localStorage.removeItem(MESSAGES_KEY)
    const newId = crypto.randomUUID().replace(/-/g, '').slice(0, 32)
    sessionIdRef.current = newId
    localStorage.setItem(SESSION_KEY, newId)
    wizard.resetWizard()
  }

  // ── Indicador de estado del backend ────────────────────────────────────────
  const statusDot =
    backendStatus === 'checking' ? '#F29A01'   // amarillo: verificando
    : backendStatus === 'online'  ? '#00B87C'  // verde: conectado
    : '#D8473A'                                // rojo: offline

  const statusLabel =
    backendStatus === 'checking' ? 'Conectando…'
    : backendStatus === 'online'  ? 'Asistente institucional'
    : 'Servicio no disponible'

  return (
    <>
      {/* ═══════════════ CHAT PANEL ═══════════════ */}
      <div
        className={`chat-widget-panel ${isOpen ? 'chat-widget-open' : 'chat-widget-closed'}`}
        style={{
          position: 'fixed',
          bottom: isFullscreen ? '0' : '96px',
          right:  isFullscreen ? '0' : '24px',
          width:  isFullscreen ? '100vw' : '520px',
          height: isFullscreen ? '100vh' : '680px',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: isFullscreen ? '0' : '16px',
          overflow: 'hidden',
          boxShadow: isOpen ? '0 12px 48px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,0,0,0.05)' : 'none',
          opacity: isOpen ? 1 : 0,
          transform: isOpen ? 'translateY(0) scale(1)' : 'translateY(20px) scale(0.95)',
          pointerEvents: isOpen ? 'auto' : 'none',
          transition: 'opacity 0.3s ease, transform 0.3s ease, width 0.3s ease, height 0.3s ease, bottom 0.3s ease, right 0.3s ease, border-radius 0.3s ease',
          background: '#F2F6F9',
        }}
      >
        {/* Panel Header */}
        <div
          style={{
            background: 'linear-gradient(135deg, #001A34 0%, #0F385A 100%)',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              background: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              overflow: 'hidden',
              border: '2px solid rgba(2,153,216,0.3)',
              flexShrink: 0,
            }}
          >
            <img
              src="/Logo_1.png"
              alt="BravoBot"
              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div
              style={{
                color: '#fff',
                fontFamily: '"Roboto Condensed", sans-serif',
                fontWeight: 700,
                fontSize: '16px',
                lineHeight: 1.2,
              }}
            >
              BravoBot
            </div>
            <div
              style={{
                color: 'rgba(255,255,255,0.65)',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: statusDot,
                  display: 'inline-block',
                  transition: 'background 0.4s',
                }}
              />
              {statusLabel}
            </div>
          </div>

          {/* New conversation button */}
          {messages.length > 0 && (
            <button
              onClick={handleNewConversation}
              style={{
                background: 'rgba(255,255,255,0.1)',
                border: 'none',
                borderRadius: '8px',
                color: '#fff',
                cursor: 'pointer',
                padding: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
              aria-label="Nueva conversación"
              title="Nueva conversación"
            >
              {/* Pencil / new-chat icon */}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
              </svg>
            </button>
          )}

          {/* Fullscreen toggle button */}
          <button
            onClick={() => setIsFullscreen((prev) => !prev)}
            style={{
              background: 'rgba(255,255,255,0.1)',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              cursor: 'pointer',
              padding: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.2s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
            aria-label={isFullscreen ? 'Restaurar tamaño' : 'Pantalla completa'}
            title={isFullscreen ? 'Restaurar tamaño' : 'Pantalla completa'}
          >
            {isFullscreen ? <RestoreIcon /> : <FullscreenIcon />}
          </button>

          {/* Close button */}
          <button
            onClick={() => setIsOpen(false)}
            style={{
              background: 'rgba(255,255,255,0.1)',
              border: 'none',
              borderRadius: '8px',
              color: '#fff',
              cursor: 'pointer',
              padding: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'background 0.2s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.1)')}
            aria-label="Cerrar chat"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Banner offline */}
        {backendStatus === 'offline' && (
          <div
            style={{
              background: '#D8473A',
              color: '#fff',
              fontSize: '11px',
              fontFamily: '"Open Sans", sans-serif',
              padding: '6px 16px',
              textAlign: 'center',
              flexShrink: 0,
            }}
          >
            ⚠️ El servicio no está disponible en este momento. Intenta más tarde.
          </div>
        )}

        {/* Chat body */}
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onSuggestion={handleSuggestion}
            onWizardStart={handleWizardStart}
            onWizardAnswer={handleWizardAnswer}
          />
          <InputBar onSend={sendMessage} disabled={isLoading || backendStatus === 'offline'} />
        </div>
      </div>

      {/* ═══════════════ FLOATING BUTTON ═══════════════ */}
      <button
        id="chat-widget-toggle"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          border: 'none',
          cursor: 'pointer',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.3s ease',
          background: isOpen
            ? 'linear-gradient(135deg, #001A34 0%, #0F385A 100%)'
            : 'linear-gradient(135deg, #0299D8 0%, #027ab5 100%)',
          color: '#fff',
          boxShadow: isOpen
            ? '0 4px 16px rgba(0,26,52,0.4)'
            : '0 4px 20px rgba(2,153,216,0.45)',
          overflow: 'hidden',
          animation: isOpen ? 'none' : 'chatWidgetPulse 3s ease-in-out infinite',
        }}
        aria-label={isOpen ? 'Cerrar chat' : 'Abrir chat con BravoBot'}
      >
        {isOpen ? (
          <CloseIcon />
        ) : (
          <img
            src="/Logo_1.png"
            alt="BravoBot"
            style={{ width: '42px', height: '42px', objectFit: 'cover', borderRadius: '50%' }}
          />
        )}
      </button>

      {/* Tooltip (only when closed) */}
      {!isOpen && (
        <div
          style={{
            position: 'fixed',
            bottom: '90px',
            right: '24px',
            background: '#001A34',
            color: '#fff',
            fontSize: '12px',
            fontFamily: '"Open Sans", sans-serif',
            fontWeight: 600,
            padding: '6px 14px',
            borderRadius: '8px',
            zIndex: 10000,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            whiteSpace: 'nowrap',
            animation: 'chatTooltipFade 0.5s ease 2s both',
            pointerEvents: 'none',
          }}
        >
          Chatea con BravoBot 💬
          <div
            style={{
              position: 'absolute',
              bottom: '-5px',
              right: '20px',
              width: '10px',
              height: '10px',
              background: '#001A34',
              transform: 'rotate(45deg)',
            }}
          />
        </div>
      )}

      {/* Animations */}
      <style>{`
        @keyframes chatWidgetPulse {
          0%, 100% { box-shadow: 0 4px 20px rgba(2,153,216,0.45); }
          50% { box-shadow: 0 4px 30px rgba(2,153,216,0.65), 0 0 0 8px rgba(2,153,216,0.1); }
        }
        @keyframes chatTooltipFade {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @media (max-width: 480px) {
          .chat-widget-panel:not(.chat-widget-fullscreen) {
            width: calc(100vw - 16px) !important;
            height: calc(100vh - 120px) !important;
            right: 8px !important;
            bottom: 80px !important;
            border-radius: 12px !important;
          }
        }
      `}</style>
    </>
  )
}
