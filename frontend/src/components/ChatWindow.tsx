import { useEffect, useRef } from 'react'
import MessageBubble, { Message } from './MessageBubble'

interface ChatWindowProps {
  messages: Message[]
  isLoading: boolean
  onSuggestion: (text: string) => void
  onWizardStart: () => void
  onWizardAnswer: (value: string) => void
  onMessageFeedback: (msg: Message, rating: 1 | -1) => Promise<void>
}

const SUGGESTIONS = [
  { icon: '🎓', text: '¿Qué programas de ingeniería ofrecen?' },
  { icon: '💰', text: '¿Cuáles son los costos de matrícula?' },
  { icon: '📋', text: '¿Cómo es el proceso de inscripción?' },
  { icon: '🏆', text: '¿Tienen becas disponibles?' },
  { icon: '📅', text: '¿Cuándo son las fechas de admisión?' },
  { icon: '🏢', text: '¿Cuál es la oferta de posgrados?' },
]

// ── Chips de seguimiento según intención y categoría ───────────────────────
const FOLLOWUP_CHIPS: Record<string, { icon: string; text: string }[]> = {
  'intent:comparison': [
    { icon: '💰', text: '¿Cuáles son los costos de cada uno?' },
    { icon: '📚', text: 'Muéstrame la malla curricular de cada uno' },
    { icon: '✨', text: '¿Cuál me recomendás según mi perfil?' },
  ],
  'intent:recommendation': [
    { icon: 'ℹ️', text: 'Más información sobre esa carrera' },
    { icon: '💰', text: '¿Cuánto cuesta estudiar ahí?' },
    { icon: '📚', text: '¿Qué materias tiene?' },
  ],
  'intent:conversational': [
    { icon: '🔍', text: 'Amplía ese punto' },
    { icon: '⚖️', text: '¿Qué programas tienen más salidas laborales?' },
  ],
  'categoria:programas': [
    { icon: '⚖️', text: 'Compara ese programa con otro' },
    { icon: '💰', text: '¿Cuánto cuesta ese programa?' },
    { icon: '📝', text: 'Resúmeme esa información' },
  ],
  'categoria:costos': [
    { icon: '🏆', text: '¿Hay becas disponibles?' },
    { icon: '⚖️', text: 'Compara costos entre programas' },
    { icon: '📝', text: 'Resúmeme esa información' },
  ],
  'categoria:admisiones': [
    { icon: '📄', text: '¿Qué documentos necesito?' },
    { icon: '📝', text: 'Resúmeme los pasos de inscripción' },
    { icon: '📅', text: '¿Cuándo son las próximas fechas?' },
  ],
  'categoria:bienestar': [
    { icon: '🌐', text: '¿Cómo es el programa de inglés?' },
    { icon: '💪', text: '¿Qué servicios deportivos ofrecen?' },
    { icon: '📝', text: 'Explícame más sobre bienestar' },
  ],
  'categoria:becas': [
    { icon: '💰', text: '¿Cuáles son los costos de matrícula?' },
    { icon: '📋', text: '¿Cómo aplico a una beca?' },
    { icon: '📝', text: 'Resúmeme los tipos de beca' },
  ],
  'default': [
    { icon: '🔍', text: 'Explícame más sobre eso' },
    { icon: '📝', text: 'Resúmeme esa respuesta' },
    { icon: '❓', text: '¿Qué más debería saber?' },
  ],
}

function getFollowupChips(msg: Message): { icon: string; text: string }[] {
  if (msg.intent && `intent:${msg.intent}` in FOLLOWUP_CHIPS) {
    return FOLLOWUP_CHIPS[`intent:${msg.intent}`]
  }
  if (msg.categoria && `categoria:${msg.categoria}` in FOLLOWUP_CHIPS) {
    return FOLLOWUP_CHIPS[`categoria:${msg.categoria}`]
  }
  return FOLLOWUP_CHIPS['default']
}

export default function ChatWindow({ messages, isLoading, onSuggestion, onWizardStart, onWizardAnswer, onMessageFeedback }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Find index of last bot message to show follow-up chips there
  const lastBotIdx = messages.reduceRight(
    (found, msg, idx) => (found === -1 && msg.role === 'bot' ? idx : found),
    -1,
  )

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">

      {/* ── Welcome / empty state ── */}
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center min-h-full gap-6 text-center animate-fade-in">

          {/* Logo mark */}
          <div className="relative">
            <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center shadow-lg shadow-pb-aqua/30 overflow-hidden border-2 border-pb-aqua/20">
              <img src="/Logo_1.png" alt="BravoBot" className="w-full h-full object-cover" />
            </div>
            {/* Online dot */}
            <span className="absolute bottom-1 right-1 w-4 h-4 bg-pb-green rounded-full border-2 border-white animate-pulse" />
          </div>

          <div className="max-w-sm">
            <h2 className="text-2xl font-heading font-bold text-pb-navy leading-tight">
              ¡Hola! Soy <span className="text-pb-aqua">BravoBot</span>
            </h2>
            <p className="mt-2 text-sm font-body text-pb-gray leading-relaxed">
              Tu asistente institucional de la{' '}
              <span className="font-semibold text-pb-navy">I.U. Pascual Bravo</span>.
              <br />
              Pregúntame sobre admisiones, programas, costos, compara carreras y más.
            </p>
          </div>

          {/* Wizard entry CTA */}
          <button
            onClick={onWizardStart}
            className="w-full max-w-lg flex items-center gap-3 rounded-2xl px-5 py-4 text-left shadow-lg transition-all duration-200 hover:shadow-xl hover:scale-[1.02] active:scale-[0.99]"
            style={{
              background: 'linear-gradient(135deg, #001A34 0%, #0F385A 100%)',
              border: '1px solid rgba(2,153,216,0.25)',
            }}
          >
            <span className="text-3xl flex-shrink-0">🎯</span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-heading font-bold text-white leading-tight">
                Ayúdame a elegir una carrera
              </div>
              <div className="text-[11px] font-body text-white/65 mt-0.5 leading-tight">
                Responde 4 preguntas rápidas y recibe recomendaciones personalizadas
              </div>
            </div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>

          {/* Suggestion chips */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
            {SUGGESTIONS.map((s) => (
              <button
                key={s.text}
                onClick={() => onSuggestion(s.text)}
                className="suggestion-chip flex items-center gap-2.5 bg-white border border-gray-200 rounded-xl px-4 py-3 text-left shadow-sm"
              >
                <span className="text-lg flex-shrink-0">{s.icon}</span>
                <span className="text-xs font-body font-medium text-pb-gray leading-snug">{s.text}</span>
              </button>
            ))}
          </div>


        </div>
      )}

      {/* ── Messages ── */}
      {messages.length > 0 && (
        <div className="space-y-5 max-w-3xl mx-auto">
          {messages.map((msg, idx) => (
            <div key={msg.id}>
              <MessageBubble
                message={msg}
                onWizardAnswer={onWizardAnswer}
                onMessageFeedback={(rating) => onMessageFeedback(msg, rating)}
              />

              {/* Follow-up chips — only after last bot message, only when not loading */}
              {!isLoading && idx === lastBotIdx && msg.role === 'bot' && !msg.wizardOptions && (
                <div className="mt-2 ml-12 flex flex-wrap gap-1.5 animate-fade-in">
                  {getFollowupChips(msg).map((chip) => (
                    <button
                      key={chip.text}
                      onClick={() => onSuggestion(chip.text)}
                      className="inline-flex items-center gap-1.5 bg-white border border-gray-200 hover:border-pb-aqua hover:text-pb-aqua rounded-full px-3 py-1 text-[11px] font-body font-medium text-pb-gray shadow-sm transition-all duration-150"
                    >
                      <span>{chip.icon}</span>
                      <span>{chip.text}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {isLoading && (
            <div className="flex gap-3 items-end animate-fade-in">
              <div className="flex-shrink-0 w-9 h-9 rounded-full bg-white flex items-center justify-center shadow-md overflow-hidden border border-pb-aqua/20">
                <img src="/Logo_1.png" alt="BravoBot" className="w-full h-full object-cover" />
              </div>
              <div className="bg-white rounded-2xl rounded-bl-sm px-5 py-4 shadow-sm border border-gray-100 flex gap-1.5 items-center">
                {[0, 160, 320].map((delay) => (
                  <span
                    key={delay}
                    className="w-2 h-2 bg-pb-aqua rounded-full animate-bounce-dot"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}
