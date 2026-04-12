// frontend/src/hooks/useWebSocket.ts
import { useCallback, useEffect, useRef, useState } from 'react'
import { ServerMessage } from '../types'

interface UseWebSocketOptions {
  url: string
  onMessage: (msg: ServerMessage) => void
  onConnect?: () => void
  onDisconnect?: () => void
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<number>()
  const isConnectingRef = useRef(false)

  // 使用 ref 存储回调，避免依赖变化导致重连
  const onMessageRef = useRef(onMessage)
  const onConnectRef = useRef(onConnect)
  const onDisconnectRef = useRef(onDisconnect)

  // 每次渲染时更新 ref
  useEffect(() => {
    onMessageRef.current = onMessage
    onConnectRef.current = onConnect
    onDisconnectRef.current = onDisconnect
  })

  const connect = useCallback(() => {
    // 防止重复连接
    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    isConnectingRef.current = true
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      isConnectingRef.current = false
      setIsConnected(true)
      onConnectRef.current?.()
    }

    ws.onclose = () => {
      isConnectingRef.current = false
      setIsConnected(false)
      onDisconnectRef.current?.()
      // 自动重连
      reconnectTimeoutRef.current = window.setTimeout(() => {
        connect()
      }, 2000)
    }

    ws.onerror = (error) => {
      isConnectingRef.current = false
      console.error('WebSocket error:', error)
    }

    ws.onmessage = (event) => {
      try {
        const msg: ServerMessage = JSON.parse(event.data)
        onMessageRef.current(msg)
      } catch (e) {
        console.error('Failed to parse message:', e)
      }
    }
  }, [url]) // 只依赖 url

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    wsRef.current?.close()
    wsRef.current = null
    setIsConnected(false)
    isConnectingRef.current = false
  }, [])

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    isConnected,
    send,
    disconnect,
    reconnect: connect,
  }
}
