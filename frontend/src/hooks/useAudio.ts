// frontend/src/hooks/useAudio.ts
import { useCallback, useRef, useState } from 'react'

const SAMPLE_RATE = 16000

export function useAudio() {
  const [isRecording, setIsRecording] = useState(false)
  const [frequencyData, setFrequencyData] = useState<Uint8Array | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const chunksRef = useRef<Int16Array[]>([])

  // 获取音频频谱数据（用于波形可视化）
  const getFrequencyData = useCallback(() => {
    if (!analyserRef.current) return null
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)
    return dataArray
  }, [])

  // 开始录音
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      mediaStreamRef.current = stream

      const audioContext = new AudioContext({ sampleRate: SAMPLE_RATE })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyserRef.current = analyser

      // 使用 ScriptProcessor 采集 PCM 数据
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      chunksRef.current = []

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0)
        // Float32 -> Int16 PCM
        const pcmData = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]))
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        }
        chunksRef.current.push(pcmData)

        // 更新频谱数据
        const freqData = getFrequencyData()
        if (freqData) {
          setFrequencyData(freqData)
        }
      }

      source.connect(analyser)
      analyser.connect(processor)
      processor.connect(audioContext.destination)

      setIsRecording(true)
    } catch (error) {
      console.error('Failed to start recording:', error)
      throw error
    }
  }, [getFrequencyData])

  // 停止录音并返回 PCM 数据
  const stopRecording = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop())
      mediaStreamRef.current = null
    }

    setIsRecording(false)
    setFrequencyData(null)

    // 合并所有 chunk
    const totalLength = chunksRef.current.reduce((sum, c) => sum + c.length, 0)
    const result = new Int16Array(totalLength)
    let offset = 0
    for (const chunk of chunksRef.current) {
      result.set(chunk, offset)
      offset += chunk.length
    }
    chunksRef.current = []

    return result
  }, [])

  return {
    isRecording,
    frequencyData,
    startRecording,
    stopRecording,
    getFrequencyData,
  }
}
