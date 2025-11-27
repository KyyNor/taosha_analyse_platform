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
  // 原生LangChain事件格式
  event: 'text' | 'tool_call' | 'tool_result' | 'error';
  data: {
    // text事件
    content?: string;
    type?: string;

    // tool_call事件
    id?: string;
    name?: string;
    args?: any;
    status?: 'pending' | 'completed' | 'failed';

    // tool_result事件
    result?: any;
    isError?: boolean;

    // error事件
    error?: string;

    // 其他通用字段
    [key: string]: any;
  };

  // 兼容字段（保留以确保向后兼容）
  type?: 'assistant_message_start' | 'text_delta' | 'tool_call_start' | 'tool_call_input' | 'tool_call_result' | 'tool_call_error' | 'assistant_message_complete' | 'done' | 'error';
  id?: string;
  role?: string;
  content?: string;
  toolCallId?: string;
  toolName?: string;
  input?: any;
  result?: any;
}