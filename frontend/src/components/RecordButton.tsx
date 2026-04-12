// frontend/src/components/RecordButton.tsx
import { ConversationState } from '../types'
import { useState, useCallback, useRef } from 'react'

interface RecordButtonProps {
  state: ConversationState
  isRecording: boolean
  onStart: () => void
  onEnd: () => void
}

export function RecordButton({
  state,
  onStart,
  onEnd,
}: RecordButtonProps) {
  const [isPressed, setIsPressed] = useState(false)
  const isDisabled = state === 'TRANSCRIBING' || state === 'THINKING'
  const pressStartRef = useRef<number>(0)

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    if (isDisabled) return
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    pressStartRef.current = Date.now()
    setIsPressed(true)
    onStart()
  }, [isDisabled, onStart])

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    if (isDisabled) return
    e.preventDefault()
    if (isPressed) {
      setIsPressed(false)
      onEnd()
    }
  }, [isDisabled, isPressed, onEnd])

  const handlePointerCancel = useCallback(() => {
    if (isDisabled) return
    if (isPressed) {
      setIsPressed(false)
      onEnd()
    }
  }, [isDisabled, isPressed, onEnd])

  const handlePointerLeave = useCallback(() => {
    if (isDisabled || !isPressed) return
    setIsPressed(false)
    onEnd()
  }, [isDisabled, isPressed, onEnd])

  return (
    <div className="hidden">
      {/* RecordButton is now hidden - interaction is handled via keyboard/other UI */}
      <button
        style={{ touchAction: 'manipulation' }}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onPointerLeave={handlePointerLeave}
        disabled={isDisabled}
      />
    </div>
  )
}
