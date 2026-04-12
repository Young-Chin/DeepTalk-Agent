// frontend/src/components/StatusText.tsx
import { motion, AnimatePresence } from 'framer-motion'
import { ConversationState, STATE_COLORS, STATE_LABELS } from '../types'

interface StatusTextProps {
  state: ConversationState
}

export function StatusText({ state }: StatusTextProps) {
  const color = STATE_COLORS[state] || STATE_COLORS.LISTENING
  const label = STATE_LABELS[state] || 'Listening'

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="relative flex items-center justify-center">
        <motion.div
          animate={{
            opacity: [0.4, 1, 0.4],
            filter: [
              `blur(8px) brightness(0.8)`,
              `blur(12px) brightness(1.2)`,
              `blur(8px) brightness(0.8)`,
            ],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute w-24 h-24 rounded-full"
          style={{
            backgroundColor: `${color}4d`,
          }}
        />
        <div
          className="w-2.5 h-2.5 rounded-full relative z-10"
          style={{
            backgroundColor: color,
            boxShadow: `0 0 20px ${color}`,
          }}
        />
      </div>
      <AnimatePresence mode="wait">
        <motion.span
          key={state}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.2 }}
          className="text-[10px] uppercase tracking-[0.4em] font-extrabold"
          style={{ color }}
        >
          {label}
        </motion.span>
      </AnimatePresence>
    </div>
  )
}
