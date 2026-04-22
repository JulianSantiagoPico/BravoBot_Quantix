import { useEffect, useRef } from 'react'
import MessageBubble, { Message } from './MessageBubble'

interface ChatWindowProps {
  messages: Message[]
  isLoading: boolean
  onSuggestion: (text: string) => void
}

const SUGGESTIONS = [
  { icon: '🎓', text: '¿Qué programas de ingeniería ofrecen?' },
  { icon: '💰', text: '¿Cuáles son los costos de matrícula?' },
  { icon: '📋', text: '¿Cómo es el proceso de inscripción?' },
  { icon: '🏆', text: '¿Tienen becas disponibles?' },
  { icon: '📅', text: '¿Cuándo son las fechas de admisión?' },
  { icon: '🏢', text: '¿Cuál es la oferta de posgrados?' },
]

export default function ChatWindow({ messages, isLoading, onSuggestion }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

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
              Pregúntame sobre admisiones, programas, costos y más.
            </p>
          </div>

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
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
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
