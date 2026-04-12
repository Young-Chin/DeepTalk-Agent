// frontend/src/components/Sidebar.tsx
import { motion, AnimatePresence } from 'framer-motion'
import { Message } from '../types'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
  onNewChat: () => void
  chatHistory: Message[][]
}

export function Sidebar({ isOpen, onToggle, onNewChat, chatHistory }: SidebarProps) {
  return (
    <>
      {/* Overlay backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/30 z-40"
            onClick={onToggle}
          />
        )}
      </AnimatePresence>

      {/* Sidebar panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ type: 'spring', damping: 24, stiffness: 200 }}
            className="fixed left-4 top-4 bottom-4 w-72 z-50 flex flex-col rounded-2xl overflow-hidden"
            style={{
              background: 'rgba(10, 12, 16, 0.75)',
              backdropFilter: 'blur(24px) saturate(180%)',
              WebkitBackdropFilter: 'blur(24px) saturate(180%)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05)',
            }}
          >
            {/* Header */}
            <div className="flex items-start justify-between p-5 border-b border-white/5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/30 to-secondary/20 border border-white/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="material-symbols-outlined text-primary text-[18px]">mic</span>
                </div>
                <div className="flex flex-col">
                  <h2 className="font-headline text-base font-semibold text-white/90">DeepTalk AI</h2>
                  <p className="text-[11px] uppercase tracking-[0.15em] text-white/30 mt-0.5">Show yourself</p>
                  <p className="text-[11px] uppercase tracking-[0.15em] text-white/30">Know yourself</p>
                </div>
              </div>
              <button
                onClick={onToggle}
                className="p-2 hover:bg-white/5 rounded-lg transition-colors"
              >
                <span className="material-symbols-outlined text-white/40 text-[18px]">close</span>
              </button>
            </div>

            {/* New Chat button */}
            <div className="px-4 pt-4">
              <button
                onClick={() => { onNewChat(); onToggle(); }}
                className="w-full py-3 rounded-xl border border-primary/20 bg-primary/5 hover:bg-primary/10 transition-all flex items-center justify-center gap-2 group"
              >
                <span className="material-symbols-outlined text-primary text-[18px]">add</span>
                <span className="text-sm text-primary font-semibold uppercase tracking-wider">New Chat</span>
              </button>
            </div>

            {/* History section */}
            <div className="flex-1 px-4 pt-5 overflow-y-auto no-scrollbar">
              <p className="text-[11px] uppercase tracking-[0.2em] text-white/25 font-bold mb-3 px-1">
                History
              </p>
              <div className="space-y-1">
                {chatHistory.length === 0 && (
                  <p className="text-sm text-white/20 px-1 py-6 text-center">
                    No conversations yet
                  </p>
                )}
                {chatHistory.map((session, index) => {
                  const firstUserMsg = session.find((m) => m.role === 'user')
                  const label = firstUserMsg
                    ? firstUserMsg.content.slice(0, 36) + (firstUserMsg.content.length > 36 ? '...' : '')
                    : `Session ${index + 1}`
                  return (
                    <button
                      key={index}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left hover:bg-white/5 transition-colors group"
                    >
                      <span className="material-symbols-outlined text-white/20 text-[18px] group-hover:text-primary/50 transition-colors flex-shrink-0">
                        history
                      </span>
                      <span className="text-sm text-white/40 group-hover:text-white/70 transition-colors truncate">
                        {label}
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Toggle button when sidebar is closed */}
      {!isOpen && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          onClick={onToggle}
          className="fixed left-6 top-6 p-3 bg-white/5 hover:bg-white/10 backdrop-blur-md border border-white/10 rounded-xl z-40 transition-all"
        >
          <span className="material-symbols-outlined text-white/50 text-[20px]">menu</span>
        </motion.button>
      )}
    </>
  )
}
