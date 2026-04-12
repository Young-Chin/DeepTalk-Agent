// frontend/src/components/ChatHistory.tsx
import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Message } from '../types'

interface ChatHistoryProps {
  messages: Message[]
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const mm = String(date.getMinutes()).padStart(2, '0')
  const ss = String(date.getSeconds()).padStart(2, '0')
  return `${mm}:${ss}`
}

export function ChatHistory({ messages }: ChatHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isOverflowing, setIsOverflowing] = useState(false)

  // Check if content overflows container
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const checkOverflow = () => {
      setIsOverflowing(container.scrollHeight > container.clientHeight)
    }

    checkOverflow()
    window.addEventListener('resize', checkOverflow)
    return () => window.removeEventListener('resize', checkOverflow)
  }, [messages])

  // Auto-scroll to bottom when new messages arrive (only when overflowing)
  useEffect(() => {
    if (bottomRef.current && isOverflowing) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, isOverflowing])

  return (
    <div className="relative w-full h-full z-20 flex flex-col">
      <div
        ref={containerRef}
        className="w-full h-full overflow-y-auto no-scrollbar px-8 pt-8"
      >
        <div
          className={`space-y-8 ${
            isOverflowing ? 'min-h-full flex flex-col justify-end' : ''
          }`}
        >
          <AnimatePresence initial={false}>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{
                  duration: 0.5,
                  ease: [0.4, 0, 0.2, 1],
                }}
              >
                {message.role === 'user' ? (
                  <>
                    <p className="text-[10px] uppercase tracking-widest text-primary font-bold">
                      Host • {formatTime(message.timestamp)}
                    </p>
                    <div className="max-w-xl">
                      <p className="text-2xl font-headline font-medium text-on-surface leading-snug">
                        {message.content}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="text-[10px] uppercase tracking-widest text-secondary font-bold">
                      Oracle • {formatTime(message.timestamp)}
                    </p>
                    <div className="max-w-xl">
                      <p className="text-3xl font-headline font-bold text-secondary-dim leading-tight italic">
                        &ldquo;{message.content}&rdquo;
                      </p>
                    </div>
                  </>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  )
}
