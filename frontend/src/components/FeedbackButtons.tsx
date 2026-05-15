import { useState } from 'react'

type FeedbackState = 'idle' | 'sending' | 'voted_up' | 'voted_down'

interface FeedbackButtonsProps {
  onVote: (rating: 1 | -1) => Promise<void>
}

export default function FeedbackButtons({ onVote }: FeedbackButtonsProps) {
  const [state, setState] = useState<FeedbackState>('idle')

  const handleVote = async (rating: 1 | -1) => {
    if (state !== 'idle') return
    setState('sending')
    await onVote(rating)
    setState(rating === 1 ? 'voted_up' : 'voted_down')
  }

  if (state === 'voted_up' || state === 'voted_down') {
    return (
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          fontSize: '11px',
          color: state === 'voted_up' ? '#00B87C' : '#D8473A',
          fontFamily: '"Open Sans", sans-serif',
          fontWeight: 600,
          marginTop: '4px',
          animation: 'fbFadeIn 0.3s ease',
        }}
      >
        <span style={{ fontSize: '14px' }}>{state === 'voted_up' ? '👍' : '👎'}</span>
        <span>¡Gracias por tu opinión!</span>
        <style>{`
          @keyframes fbFadeIn {
            from { opacity: 0; transform: translateY(3px); }
            to   { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </div>
    )
  }

  const isSending = state === 'sending'

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        marginTop: '6px',
        opacity: isSending ? 0.5 : 1,
        transition: 'opacity 0.2s',
      }}
      aria-label="¿Fue útil esta respuesta?"
    >
      <span
        style={{
          fontSize: '10px',
          color: '#9CA3AF',
          fontFamily: '"Open Sans", sans-serif',
          userSelect: 'none',
        }}
      >
        ¿Útil?
      </span>

      {/* 👍 */}
      <button
        id={`fb-up-${Math.random().toString(36).slice(2)}`}
        onClick={() => handleVote(1)}
        disabled={isSending}
        aria-label="Respuesta útil"
        title="Respuesta útil"
        style={{
          background: 'none',
          border: '1px solid #E5E7EB',
          borderRadius: '20px',
          cursor: isSending ? 'not-allowed' : 'pointer',
          padding: '3px 8px',
          fontSize: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
          color: '#6B7280',
          fontFamily: '"Open Sans", sans-serif',
          transition: 'all 0.15s ease',
          lineHeight: 1,
        }}
        onMouseEnter={(e) => {
          if (!isSending) {
            e.currentTarget.style.background = '#F0FDF4'
            e.currentTarget.style.borderColor = '#00B87C'
            e.currentTarget.style.color = '#00B87C'
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'none'
          e.currentTarget.style.borderColor = '#E5E7EB'
          e.currentTarget.style.color = '#6B7280'
        }}
      >
        👍
      </button>

      {/* 👎 */}
      <button
        id={`fb-down-${Math.random().toString(36).slice(2)}`}
        onClick={() => handleVote(-1)}
        disabled={isSending}
        aria-label="Respuesta no útil"
        title="Respuesta no útil"
        style={{
          background: 'none',
          border: '1px solid #E5E7EB',
          borderRadius: '20px',
          cursor: isSending ? 'not-allowed' : 'pointer',
          padding: '3px 8px',
          fontSize: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
          color: '#6B7280',
          fontFamily: '"Open Sans", sans-serif',
          transition: 'all 0.15s ease',
          lineHeight: 1,
        }}
        onMouseEnter={(e) => {
          if (!isSending) {
            e.currentTarget.style.background = '#FEF2F2'
            e.currentTarget.style.borderColor = '#D8473A'
            e.currentTarget.style.color = '#D8473A'
          }
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'none'
          e.currentTarget.style.borderColor = '#E5E7EB'
          e.currentTarget.style.color = '#6B7280'
        }}
      >
        👎
      </button>
    </div>
  )
}
