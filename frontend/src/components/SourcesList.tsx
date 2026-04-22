import { useState } from 'react'

interface SourcesListProps {
  fuentes: string[]
}

// Truncate long URLs to a readable hostname + path
function shortUrl(url: string): string {
  try {
    const { hostname, pathname } = new URL(url)
    const path = pathname.length > 30 ? pathname.slice(0, 28) + '…' : pathname
    return hostname + path
  } catch {
    return url.length > 50 ? url.slice(0, 48) + '…' : url
  }
}

// Icon: external link
function ExternalIcon() {
  return (
    <svg className="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
      />
    </svg>
  )
}

export default function SourcesList({ fuentes }: SourcesListProps) {
  const [open, setOpen] = useState(false)

  if (!fuentes || fuentes.length === 0) return null

  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[11px] font-body font-medium text-pb-aqua hover:text-[#027ab5] transition-colors group"
        aria-expanded={open}
      >
        {/* Chevron icon */}
        <svg
          className={`w-3 h-3 transition-transform duration-200 ${open ? 'rotate-90' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="underline underline-offset-2">
          {open ? 'Ocultar fuentes' : `${fuentes.length} fuente${fuentes.length > 1 ? 's' : ''} oficial${fuentes.length > 1 ? 'es' : ''}`}
        </span>
      </button>

      {open && (
        <ul className="mt-2 space-y-1.5 pl-4 border-l-2 border-pb-aqua/30 animate-fade-in">
          {fuentes.map((url, i) => (
            <li key={i} className="flex items-center gap-1.5">
              <ExternalIcon />
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] font-body text-pb-aqua hover:text-[#027ab5] transition-colors truncate max-w-[280px]"
                title={url}
              >
                {shortUrl(url)}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
