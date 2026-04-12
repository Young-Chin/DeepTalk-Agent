// frontend/src/types.ts

export type ConversationState =
  | 'DREAMING'
  | 'LISTENING'
  | 'TRANSCRIBING'
  | 'THINKING'
  | 'SPEAKING'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

// WebSocket 消息类型
export type WSMessageType =
  | 'audio_start'
  | 'audio_chunk'
  | 'audio_stop'
  | 'interrupt'
  | 'state'
  | 'transcript'
  | 'reply_chunk'
  | 'reply_done'
  | 'audio_out'
  | 'audio_done'
  | 'error'

export interface StateMessage {
  type: 'state'
  state: ConversationState
}

export interface TranscriptMessage {
  type: 'transcript'
  text: string
  role: 'user'
}

export interface ReplyChunkMessage {
  type: 'reply_chunk'
  text: string
}

export interface ReplyDoneMessage {
  type: 'reply_done'
  text: string
}

export interface AudioOutMessage {
  type: 'audio_out'
  data: string // base64
}

export interface AudioDoneMessage {
  type: 'audio_done'
}

export interface ErrorMessage {
  type: 'error'
  message: string
}

export type ServerMessage =
  | StateMessage
  | TranscriptMessage
  | ReplyChunkMessage
  | ReplyDoneMessage
  | AudioOutMessage
  | AudioDoneMessage
  | ErrorMessage

// 状态颜色 - 匹配原型
export const STATE_COLORS: Record<ConversationState, string> = {
  DREAMING: '#8b5cf6',    // 紫色
  LISTENING: '#69f6b8',   // 绿色
  TRANSCRIBING: '#fbbf24', // 黄色
  THINKING: '#fbbf24',     // 黄色
  SPEAKING: '#34b5fa',     // 蓝色
}

export const STATE_LABELS: Record<ConversationState, string> = {
  DREAMING: 'Dreaming',
  LISTENING: 'Listening',
  TRANSCRIBING: 'Thinking',
  THINKING: 'Thinking',
  SPEAKING: 'Speaking',
}
