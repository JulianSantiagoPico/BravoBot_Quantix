import SourcesList from './SourcesList'

export interface Message {
  id: string
  role: 'user' | 'bot'
  content: string
  fuentes?: string[]
  categoria?: string
}

// ── Category badge colours ──────────────────────────────────────────────────
const CATEGORIA_MAP: Record<string, { label: string; color: string }> = {
  admisiones: { label: 'Admisiones', color: '#0299D8' },
  programas: { label: 'Programas', color: '#4E3D98' },
  costos: { label: 'Costos', color: '#F29A01' },
  bienestar: { label: 'Bienestar', color: '#00B87C' },
  noticias: { label: 'Noticias', color: '#D8473A' },
  general: { label: 'General', color: '#4E4E4E' },
}

function CategoriaBadge({ categoria }: { categoria: string }) {
  const meta = CATEGORIA_MAP[categoria.toLowerCase()] ?? {
    label: categoria,
    color: '#4E4E4E',
  }
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-heading font-bold uppercase tracking-wider px-2 py-0.5 rounded-full text-white"
      style={{ backgroundColor: meta.color }}
    >
      {meta.label}
    </span>
  )
}

interface MessageBubbleProps {
  message: Message
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : 'flex-row'} items-end`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-xs font-heading font-bold shadow-md overflow-hidden ${isUser
            ? 'bg-gradient-to-br from-pb-navy to-pb-navy-dark text-white'
            : 'bg-white border border-pb-aqua/20'
          }`}
      >
        {isUser ? 'Tú' : <img src="/Logo_1.png" alt="BravoBot" className="w-full h-full object-cover" />}
      </div>

      {/* Content column */}
      <div className={`max-w-[78%] flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>

        {/* Category badge (bot only) */}
        {!isUser && message.categoria && (
          <CategoriaBadge categoria={message.categoria} />
        )}

        {/* Bubble */}
        <div
          className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${isUser
              ? 'bg-gradient-to-br from-pb-navy to-pb-navy-dark text-white rounded-br-sm shadow-md'
              : 'bg-white text-pb-navy rounded-bl-sm shadow-sm border border-gray-100'
            }`}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap font-body">{message.content}</span>
          ) : (
            <div
              className="bot-prose font-body whitespace-pre-wrap"
              dangerouslySetInnerHTML={{
                __html: message.content
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\n/g, '<br/>'),
              }}
            />
          )}
        </div>

        {/* Sources (bot only) */}
        {!isUser && message.fuentes && message.fuentes.length > 0 && (
          <div className="px-1">
            <SourcesList fuentes={message.fuentes} />
          </div>
        )}
      </div>
    </div>
  )
}
