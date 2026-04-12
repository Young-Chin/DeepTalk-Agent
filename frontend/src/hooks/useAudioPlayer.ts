// frontend/src/hooks/useAudioPlayer.ts
import { useCallback, useEffect, useRef, useState } from 'react'

export function useAudioPlayer() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [frequencyData, setFrequencyData] = useState<Uint8Array | null>(null)

  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<AudioBufferSourceNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const isPlayingRef = useRef(false)

  // 在用户交互时初始化 AudioContext
  const initAudioContext = useCallback(async () => {
    if (!audioContextRef.current) {
      // 创建 AudioContext 时添加更多错误处理
      try {
        audioContextRef.current = new AudioContext()
        analyserRef.current = audioContextRef.current.createAnalyser()
        analyserRef.current.fftSize = 256
        analyserRef.current.connect(audioContextRef.current.destination)
        console.log('[AudioPlayer] AudioContext created successfully')
      } catch (error) {
        console.error('[AudioPlayer] Failed to create AudioContext:', error)
        throw error
      }
    }

    // 如果 AudioContext 处于暂停状态，恢复它
    if (audioContextRef.current.state === 'suspended') {
      try {
        await audioContextRef.current.resume()
        console.log('[AudioPlayer] AudioContext resumed')
      } catch (error) {
        console.error('[AudioPlayer] Failed to resume AudioContext:', error)
        throw error
      }
    }

    return audioContextRef.current
  }, [])

  // 监听用户交互以解锁 AudioContext
  useEffect(() => {
    const unlockAudio = async () => {
      console.log('[AudioPlayer] User interaction detected, unlocking audio...')
      try {
        if (!audioContextRef.current) {
          audioContextRef.current = new AudioContext()
          analyserRef.current = audioContextRef.current.createAnalyser()
          analyserRef.current.fftSize = 256
          analyserRef.current.connect(audioContextRef.current.destination)
          console.log('[AudioPlayer] AudioContext created on user interaction')
        }
        if (audioContextRef.current.state === 'suspended') {
          await audioContextRef.current.resume()
          console.log('[AudioPlayer] AudioContext resumed on user interaction')
        }
      } catch (error) {
        console.error('[AudioPlayer] Failed to unlock audio:', error)
      }
    }

    // 监听各种用户交互事件（使用 once: true 确保只触发一次）
    document.addEventListener('click', unlockAudio, { once: true })
    document.addEventListener('keydown', unlockAudio, { once: true })
    document.addEventListener('touchstart', unlockAudio, { once: true })

    return () => {
      document.removeEventListener('click', unlockAudio)
      document.removeEventListener('keydown', unlockAudio)
      document.removeEventListener('touchstart', unlockAudio)
    }
  }, [])

  // 播放 WAV 音频
  const playAudio = useCallback(async (wavBase64: string) => {
    console.log('[AudioPlayer] playAudio called, data length:', wavBase64?.length)
    try {
      // 确保 AudioContext 已初始化并处于运行状态
      const audioContext = await initAudioContext()
      const analyser = analyserRef.current

      if (!audioContext || !analyser) {
        throw new Error('AudioContext not initialized')
      }

      // 最终检查并确保 AudioContext 处于运行状态
      if (audioContext.state !== 'running') {
        console.warn('[AudioPlayer] AudioContext state is', audioContext.state, '- attempting to resume')
        try {
          await audioContext.resume()
        } catch (e) {
          console.error('[AudioPlayer] Failed to resume AudioContext:', e)
          throw new Error(`AudioContext cannot be resumed: ${audioContext.state}`)
        }
      }

      // 解码 base64 - 使用更可靠的方法
      const base64ToBytes = (base64: string): Uint8Array => {
        const binString = atob(base64);
        const bytes = new Uint8Array(binString.length);
        for (let i = 0; i < binString.length; i++) {
          bytes[i] = binString.charCodeAt(i);
        }
        return bytes;
      };
      const bytes = base64ToBytes(wavBase64);
      console.log('[AudioPlayer] Decoded bytes:', bytes.length)

      // 解码 WAV
      console.log('[AudioPlayer] Decoding audio data...')
      const arrayBuffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer
      let audioBuffer: AudioBuffer
      try {
        audioBuffer = await audioContext.decodeAudioData(arrayBuffer)
      } catch (decodeError) {
        console.error('[AudioPlayer] Failed to decode audio data:', decodeError)
        throw new Error('Audio data decoding failed')
      }
      console.log('[AudioPlayer] Audio decoded, duration:', audioBuffer.duration)

      // 创建源
      const source = audioContext.createBufferSource()
      source.buffer = audioBuffer
      source.connect(analyser)
      sourceRef.current = source

      setIsPlaying(true)
      isPlayingRef.current = true

      // 更新频谱数据 - 使用 ref 来避免闭包问题
      const updateFrequency = () => {
        if (!isPlayingRef.current || !analyserRef.current) return
        const data = new Uint8Array(analyserRef.current.frequencyBinCount)
        analyserRef.current.getByteFrequencyData(data)
        setFrequencyData(data)
        animationFrameRef.current = requestAnimationFrame(updateFrequency)
      }
      updateFrequency()

      return new Promise<void>((resolve) => {
        source.onended = () => {
          console.log('[AudioPlayer] Playback ended')
          if (animationFrameRef.current) {
            cancelAnimationFrame(animationFrameRef.current)
          }
          setIsPlaying(false)
          isPlayingRef.current = false
          setFrequencyData(null)
          sourceRef.current = null
          resolve()
        }
        console.log('[AudioPlayer] Starting playback...')
        source.start()
      })
    } catch (error) {
      console.error('[AudioPlayer] Failed to play audio:', error)
      setIsPlaying(false)
      isPlayingRef.current = false
      throw error
    }
  }, [initAudioContext])

  // 停止播放
  const stop = useCallback(() => {
    isPlayingRef.current = false
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    if (sourceRef.current) {
      try {
        sourceRef.current.stop()
      } catch {}
      sourceRef.current = null
    }
    setIsPlaying(false)
    setFrequencyData(null)
  }, [])

  return {
    isPlaying,
    frequencyData,
    playAudio,
    stop,
  }
}
