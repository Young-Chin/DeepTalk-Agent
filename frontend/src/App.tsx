// frontend/src/App.tsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { ConversationState, Message, ServerMessage } from './types'
import { useWebSocket } from './hooks/useWebSocket'
import { useAudio } from './hooks/useAudio'
import { useAudioPlayer } from './hooks/useAudioPlayer'
import { Waveform } from './components/Waveform'
import { StatusText } from './components/StatusText'
import { ChatHistory } from './components/ChatHistory'
import { Sidebar } from './components/Sidebar'

// PCM Int16Array -> Base64
function pcmToBase64(pcm: Int16Array): string {
  const bytes = new Uint8Array(pcm.buffer)
  let binary = ''
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}

export default function App() {
  const [state, setState] = useState<ConversationState>('DREAMING')
  const [messages, setMessages] = useState<Message[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState<Message[][]>([])

  const pendingReplyRef = useRef<string>('')
  const audioQueueRef = useRef<string[]>([])
  const isPlayingRef = useRef(false)
  const isProcessingQueueRef = useRef(false)

  const { isRecording, frequencyData: micFrequencyData, startRecording, stopRecording } = useAudio()
  const { frequencyData: playerFrequencyData, playAudio, stop: stopPlayback } = useAudioPlayer()

  const processAudioQueue = useCallback(async () => {
    if (isProcessingQueueRef.current) return
    isProcessingQueueRef.current = true
    while (audioQueueRef.current.length > 0 && !isPlayingRef.current) {
      isPlayingRef.current = true
      const audioData = audioQueueRef.current.shift()!
      try { await playAudio(audioData) } catch (e) { console.error('Playback error:', e) }
      isPlayingRef.current = false
    }
    isProcessingQueueRef.current = false
  }, [playAudio])

  const handleWSMessage = useCallback((msg: ServerMessage) => {
    console.log('[WebSocket] Received:', msg.type, msg)
    switch (msg.type) {
      case 'state': setState(msg.state); break
      case 'transcript':
        setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'user', content: msg.text, timestamp: Date.now() }])
        break
      case 'reply_chunk': pendingReplyRef.current += msg.text; break
      case 'reply_done':
        setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'assistant', content: msg.text, timestamp: Date.now() }])
        pendingReplyRef.current = ''
        break
      case 'audio_out':
        console.log('[Audio] Received audio data, length:', msg.data?.length)
        audioQueueRef.current.push(msg.data)
        processAudioQueue()
        break
      case 'audio_done':
        console.log('[Audio] Audio done')
        break
      case 'error': console.error('Server error:', msg.message); break
    }
  }, [processAudioQueue])

  const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  // 开发模式：连接到 Vite 代理的 /ws（代理转发到后端 8080）
  // 生产模式：直接连接到 /ws（后端托管前端）
  const wsUrl = `${wsProtocol}://${window.location.host}/ws`
  const { isConnected, send } = useWebSocket({ url: wsUrl, onMessage: handleWSMessage })

  const currentFrequencyData = isRecording ? micFrequencyData : playerFrequencyData

  // 开始录音 - 任何状态都可以打断
  const handleRecordStart = useCallback(async () => {
    // 从 DREAMING 状态切换到 LISTENING
    if (state === 'DREAMING') {
      setState('LISTENING')
    }
    // 打断当前播放/处理
    if (state === 'SPEAKING') {
      stopPlayback()
      audioQueueRef.current = []
      isPlayingRef.current = false
    }
    if (state !== 'LISTENING') {
      send({ type: 'interrupt' })
    }

    send({ type: 'audio_start' })
    await startRecording()
  }, [state, stopPlayback, send, startRecording])

  const handleRecordStop = useCallback(() => {
    const pcmData = stopRecording()
    if (pcmData && pcmData.length > 0) {
      const base64 = pcmToBase64(pcmData)
      const chunkSize = 8192
      for (let i = 0; i < base64.length; i += chunkSize) {
        send({ type: 'audio_chunk', data: base64.slice(i, i + chunkSize) })
      }
    }
    send({ type: 'audio_stop' })
  }, [stopRecording, send])

  // 空格键切换录音 - 任何状态可打断
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code !== 'Space') return
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      e.preventDefault()
      if (isRecording) {
        handleRecordStop()
      } else {
        handleRecordStart()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isRecording, handleRecordStart, handleRecordStop])

  const handleNewChat = useCallback(() => {
    if (messages.length > 0) {
      setChatHistory((prev) => [messages, ...prev])
    }
    setMessages([])
    pendingReplyRef.current = ''
    audioQueueRef.current = []
    isPlayingRef.current = false
    isProcessingQueueRef.current = false
    stopPlayback()
  }, [messages, stopPlayback])

  return (
    <div className="relative h-screen w-screen bg-[#05070a] flex flex-col items-center justify-center overflow-hidden font-body">
      {/* Background Glow */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-500/5 rounded-full blur-[120px]" />
        <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-purple-500/5 rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <header className="absolute top-0 left-0 right-0 p-6 flex items-center justify-end z-30">
        {!isConnected && (
          <span className="text-error text-[10px] font-bold uppercase tracking-widest mr-4">
            Disconnected
          </span>
        )}
        <div className="flex items-center gap-4">
          <button className="material-symbols-outlined text-white/30 hover:text-white/70 transition-colors text-[20px]">
            settings
          </button>
          <button className="material-symbols-outlined text-white/30 hover:text-white/70 transition-colors text-[20px]">
            account_circle
          </button>
        </div>
      </header>

      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        onNewChat={handleNewChat}
        chatHistory={chatHistory}
      />

      {/* Main Content */}
      <main className="flex-1 w-full flex flex-col items-center justify-center z-10 overflow-hidden">
        {/* 3D Orb */}
        <div className="flex-shrink-0">
          <Waveform
            state={state}
            frequencyData={currentFrequencyData}
            isRecording={isRecording}
          />
        </div>

        {/* Dialogue Area */}
        {messages.length > 0 && (
          <div className="flex-1 w-full min-h-0 flex justify-center pt-4">
            <div className="w-full max-w-2xl h-full">
              <ChatHistory messages={messages} />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full p-8 flex flex-col items-center gap-5 z-20">
        <StatusText state={state} />

        <p className={`text-[10px] uppercase tracking-widest transition-opacity duration-300 ${isRecording ? 'opacity-0' : 'text-white/20'}`}>
          Press Space to record
        </p>
      </footer>
    </div>
  )
}
