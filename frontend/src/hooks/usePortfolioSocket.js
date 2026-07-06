import { useEffect, useRef, useState } from 'react'
import { API_URL } from '../api/client'
import { useAuth } from '../store/auth'

const WS_URL = API_URL.replace(/^http/, 'ws')

// Live portfolio feed. Reconnects with capped backoff; hands the latest
// portfolio_update message to the caller as plain state.
export function usePortfolioSocket() {
  const token = useAuth((s) => s.token)
  const [update, setUpdate] = useState(null)
  const [connected, setConnected] = useState(false)
  const retryRef = useRef(0)

  useEffect(() => {
    if (!token) return undefined

    let socket
    let closedByUs = false
    let retryTimer

    const connect = () => {
      socket = new WebSocket(`${WS_URL}/ws/portfolio?token=${encodeURIComponent(token)}`)

      socket.onopen = () => {
        retryRef.current = 0
        setConnected(true)
      }
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data)
        if (message.type === 'portfolio_update') setUpdate(message)
      }
      socket.onclose = () => {
        setConnected(false)
        if (closedByUs) return
        const delay = Math.min(30_000, 1000 * 2 ** retryRef.current)
        retryRef.current += 1
        retryTimer = setTimeout(connect, delay)
      }
      socket.onerror = () => socket.close()
    }

    connect()
    return () => {
      closedByUs = true
      clearTimeout(retryTimer)
      socket?.close()
    }
  }, [token])

  return { update, connected }
}
