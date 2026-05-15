import { useState } from 'react'

type ModalState = 'idle' | 'sending' | 'success'

interface RatingModalProps {
  onSubmit: (rating: number, comment: string) => Promise<void>
  onSkip: () => void
}

const MAX_COMMENT = 500

export default function RatingModal({ onSubmit, onSkip }: RatingModalProps) {
  const [hovered, setHovered]   = useState(0)
  const [selected, setSelected] = useState(0)
  const [comment, setComment]   = useState('')
  const [modalState, setModalState] = useState<ModalState>('idle')

  const displayRating = hovered || selected

  const STAR_LABELS = ['', 'Muy mala', 'Mala', 'Regular', 'Buena', '¡Excelente!']

  const handleSubmit = async () => {
    if (!selected || modalState !== 'idle') return
    setModalState('sending')
    await onSubmit(selected, comment.trim())
    setModalState('success')
    // Esperar animación de éxito y luego cerrar
    setTimeout(onSkip, 1500)
  }

  return (
    <>
      {/* ── Overlay ── */}
      <div
        onClick={onSkip}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 26, 52, 0.55)',
          backdropFilter: 'blur(4px)',
          zIndex: 10001,
          animation: 'rmOverlayIn 0.25s ease',
        }}
      />

      {/* ── Modal card ── */}
      <div
        style={{
          position: 'fixed',
          bottom: '100px',
          right: '24px',
          width: '340px',
          background: '#fff',
          borderRadius: '20px',
          boxShadow: '0 24px 64px rgba(0,26,52,0.22), 0 0 0 1px rgba(0,0,0,0.06)',
          zIndex: 10002,
          overflow: 'hidden',
          animation: 'rmCardIn 0.3s cubic-bezier(0.34,1.56,0.64,1)',
          fontFamily: '"Open Sans", sans-serif',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            background: 'linear-gradient(135deg, #001A34 0%, #0F385A 100%)',
            padding: '18px 20px 16px',
          }}
        >
          <div style={{ color: '#fff', fontSize: '15px', fontWeight: 700, fontFamily: '"Roboto Condensed", sans-serif' }}>
            ¿Cómo fue tu experiencia?
          </div>
          <div style={{ color: 'rgba(255,255,255,0.6)', fontSize: '11px', marginTop: '3px' }}>
            Tu opinión nos ayuda a mejorar BravoBot
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '20px' }}>

          {modalState === 'success' ? (
            /* ── Estado éxito ── */
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 0',
                animation: 'rmFadeIn 0.3s ease',
              }}
            >
              <span style={{ fontSize: '40px' }}>🎉</span>
              <div style={{ fontWeight: 700, color: '#001A34', fontSize: '14px' }}>
                ¡Gracias por tu calificación!
              </div>
              <div style={{ color: '#6B7280', fontSize: '12px', textAlign: 'center' }}>
                Tu feedback nos ayuda a mejorar las respuestas.
              </div>
            </div>
          ) : (
            <>
              {/* ── Estrellas ── */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      id={`rating-star-${star}`}
                      aria-label={`${star} estrellas`}
                      onClick={() => setSelected(star)}
                      onMouseEnter={() => setHovered(star)}
                      onMouseLeave={() => setHovered(0)}
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        padding: '2px',
                        fontSize: displayRating >= star ? '32px' : '28px',
                        filter: displayRating >= star ? 'none' : 'grayscale(1) opacity(0.35)',
                        transform: displayRating >= star ? 'scale(1.12)' : 'scale(1)',
                        transition: 'all 0.15s ease',
                        lineHeight: 1,
                      }}
                    >
                      ⭐
                    </button>
                  ))}
                </div>

                {/* Etiqueta semántica */}
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: displayRating ? '#0299D8' : '#9CA3AF',
                    minHeight: '18px',
                    transition: 'color 0.2s',
                  }}
                >
                  {STAR_LABELS[displayRating] ?? ''}
                </div>
              </div>

              {/* ── Comentario ── */}
              <div style={{ marginBottom: '16px' }}>
                <textarea
                  id="rating-comment"
                  placeholder="¿Qué podríamos mejorar? (opcional)"
                  value={comment}
                  onChange={(e) => setComment(e.target.value.slice(0, MAX_COMMENT))}
                  rows={3}
                  style={{
                    width: '100%',
                    border: '1px solid #E5E7EB',
                    borderRadius: '10px',
                    padding: '10px 12px',
                    fontSize: '12px',
                    fontFamily: '"Open Sans", sans-serif',
                    color: '#374151',
                    resize: 'none',
                    outline: 'none',
                    boxSizing: 'border-box',
                    transition: 'border-color 0.2s',
                  }}
                  onFocus={(e) => (e.currentTarget.style.borderColor = '#0299D8')}
                  onBlur={(e) => (e.currentTarget.style.borderColor = '#E5E7EB')}
                />
                <div style={{ textAlign: 'right', fontSize: '10px', color: '#9CA3AF', marginTop: '2px' }}>
                  {comment.length}/{MAX_COMMENT}
                </div>
              </div>

              {/* ── Botones ── */}
              <div style={{ display: 'flex', gap: '8px' }}>
                {/* Saltar */}
                <button
                  id="rating-skip"
                  onClick={onSkip}
                  style={{
                    flex: '0 0 auto',
                    background: 'none',
                    border: '1px solid #E5E7EB',
                    borderRadius: '10px',
                    padding: '9px 14px',
                    fontSize: '12px',
                    fontFamily: '"Open Sans", sans-serif',
                    color: '#6B7280',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#9CA3AF'
                    e.currentTarget.style.color = '#374151'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#E5E7EB'
                    e.currentTarget.style.color = '#6B7280'
                  }}
                >
                  Saltar
                </button>

                {/* Enviar */}
                <button
                  id="rating-submit"
                  onClick={handleSubmit}
                  disabled={!selected || modalState === 'sending'}
                  style={{
                    flex: 1,
                    background: selected
                      ? 'linear-gradient(135deg, #0299D8 0%, #027ab5 100%)'
                      : '#E5E7EB',
                    border: 'none',
                    borderRadius: '10px',
                    padding: '9px 14px',
                    fontSize: '12px',
                    fontFamily: '"Open Sans", sans-serif',
                    fontWeight: 700,
                    color: selected ? '#fff' : '#9CA3AF',
                    cursor: selected ? 'pointer' : 'not-allowed',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px',
                  }}
                >
                  {modalState === 'sending' ? (
                    <>
                      <span
                        style={{
                          width: '12px',
                          height: '12px',
                          border: '2px solid rgba(255,255,255,0.4)',
                          borderTopColor: '#fff',
                          borderRadius: '50%',
                          display: 'inline-block',
                          animation: 'rmSpin 0.8s linear infinite',
                        }}
                      />
                      Enviando…
                    </>
                  ) : (
                    'Enviar calificación'
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* ── Animaciones ── */}
      <style>{`
        @keyframes rmOverlayIn {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
        @keyframes rmCardIn {
          from { opacity: 0; transform: translateY(16px) scale(0.96); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes rmFadeIn {
          from { opacity: 0; transform: scale(0.95); }
          to   { opacity: 1; transform: scale(1); }
        }
        @keyframes rmSpin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </>
  )
}
