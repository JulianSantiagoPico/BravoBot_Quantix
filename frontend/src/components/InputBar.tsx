import { useState, useRef, KeyboardEvent } from 'react'

interface InputBarProps {
  onSend: (text: string) => void
  disabled: boolean
}

// Send icon
function SendIcon({ active }: { active: boolean }) {
  return (
    <svg
      className="w-5 h-5 transition-transform duration-150 group-hover:translate-x-0.5"
      fill="none" stroke="currentColor" viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d={active ? 'M5 12h14M12 5l7 7-7 7' : 'M12 19l9 2-9-18-9 18 9-2zm0 0v-8'}
      />
    </svg>
  )
}

export default function InputBar({ onSend, disabled }: InputBarProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const canSend = value.trim().length > 0 && !disabled

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }

  return (
    <div className="border-t border-gray-200 bg-white/80 backdrop-blur-sm px-4 pt-3 pb-4 flex-shrink-0">
      <div className="max-w-3xl mx-auto">
        {/* Input row */}
        <div
          className={`flex items-end gap-2.5 rounded-2xl border transition-all duration-200 bg-white shadow-sm px-4 py-2.5 ${
            disabled
              ? 'border-gray-200 opacity-70'
              : 'border-gray-300 focus-within:border-pb-aqua focus-within:shadow-md focus-within:shadow-pb-aqua/10'
          }`}
        >
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            id="chat-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            disabled={disabled}
            rows={1}
            placeholder="Escribe tu pregunta aquí…"
            className="flex-1 resize-none bg-transparent text-sm font-body text-pb-navy placeholder:text-gray-400
                       focus:outline-none disabled:cursor-not-allowed
                       max-h-36 overflow-y-auto leading-relaxed py-1"
            style={{ minHeight: '28px' }}
            aria-label="Campo de mensaje"
          />

          {/* Send button */}
          <button
            id="send-btn"
            onClick={handleSend}
            disabled={!canSend}
            className={`group flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
              canSend
                ? 'bg-pb-aqua text-white shadow-md shadow-pb-aqua/30 hover:bg-[#027ab5] active:scale-95'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
            aria-label="Enviar mensaje"
          >
            <SendIcon active={canSend} />
          </button>
        </div>

        {/* Footer hint */}
        <p className="mt-2 text-center text-[10px] font-body text-gray-400 leading-none">
          BravoBot responde únicamente con información oficial de{' '}
          <a
            href="https://pascualbravo.edu.co"
            target="_blank" rel="noopener noreferrer"
            className="text-pb-aqua hover:underline"
          >
            pascualbravo.edu.co
          </a>
          {' '}• Enter para enviar, Shift+Enter nueva línea
        </p>
      </div>
    </div>
  )
}
