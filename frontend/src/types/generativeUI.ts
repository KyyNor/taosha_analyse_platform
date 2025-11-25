/**
 * 生成式UI相关类型定义
 */

/**
 * Vercel AI SDK 消息部分类型
 */
export type MessagePart =
  | {
      type: 'text';
      text: string;
    }
  | {
      type: 'tool-call';
      toolCallId: string;
      toolName: string;
      args?: any;
    }
  | {
      type: 'tool-result';
      toolCallId: string;
      toolName: string;
      result: any;
      isError?: boolean;
    };

/**
 * 生成式UI消息类型
 */
export interface GenerativeUIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  parts?: MessagePart[];
  content?: string; // 兼容字段
  createdAt?: Date;
}

/**
 * SSE事件类型
 */
export type SSEEventType =
  | 'assistant_message_start'
  | 'text_delta'
  | 'tool_call_start'
  | 'tool_call_input'
  | 'tool_call_result'
  | 'tool_call_error'
  | 'assistant_message_complete'
  | 'done'
  | 'error';

/**
 * SSE事件数据结构
 */
export interface SSEEvent {
  type: SSEEventType;
  // 以下字段根据不同事件类型选择性存在
  id?: string;
  role?: string;
  content?: string;
  toolCallId?: string;
  toolName?: string;
  input?: any;
  result?: any;
  error?: string;
}

/**
 * 天气数据类型
 */
export interface WeatherData {
  province?: string;
  city: string;
  adcode?: string;
  weather: string;
  temperature: number;
  wind_direction?: string;
  wind_power?: string;
  humidity?: number;
  report_time?: string;
}

/**
 * 工具调用状态
 */
export interface ToolCallState {
  id: string;
  name: string;
  status: 'pending' | 'input-available' | 'executing' | 'completed' | 'error';
  input?: any;
  result?: any;
  error?: string;
}

/**
 * 聊天请求类型
 */
export interface ChatRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  conversation_history?: Array<{
    role: string;
    content: string;
  }>;
}
