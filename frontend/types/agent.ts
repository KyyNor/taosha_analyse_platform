/**
 * Agent相关类型定义
 */

export interface MessagePart {
  type: 'text' | 'tool-call' | 'tool-result';
  text?: string;
  toolCallId?: string;
  toolName?: string;
  args?: any;
  result?: any;
  isError?: boolean;
}

export interface SSEEvent {
  type: 'assistant_message_start' | 'text_delta' | 'tool_call_start' | 'tool_call_input' | 'tool_call_result' | 'tool_call_error' | 'assistant_message_complete' | 'done' | 'error';
  id?: string;
  role?: string;
  content?: string;
  toolCallId?: string;
  toolName?: string;
  input?: any;
  result?: any;
  error?: string;
}