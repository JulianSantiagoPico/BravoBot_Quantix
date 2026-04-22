import { useState, useEffect } from 'react'
import { getHealth } from '../services/api'

type BackendStatus = 'checking' | 'online' | 'offline'

/**
 * Hook que verifica el estado del backend al montar el widget.
 * Muestra "offline" si /health no responde en el timeout definido en api.ts.
 */
export function useHealthCheck() {
  const [status, setStatus] = useState<BackendStatus>('checking')

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then(() => { if (!cancelled) setStatus('online') })
      .catch(() => { if (!cancelled) setStatus('offline') })
    return () => { cancelled = true }
  }, [])

  return status
}
