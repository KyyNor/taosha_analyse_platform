import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from '@copilotkit/runtime';
import OpenAI from "openai";
import { NextRequest } from 'next/server';

// const model = new ChatOpenAI({ 
//     model: "kimi-k2-0905-preview", 
//     apiKey: process.env.OPENAI_API_KEY,
//     configuration: {
//         baseURL: 'https://api.openai.com/v1', 
//     },
// });
// const serviceAdapter = new LangChainAdapter({
//     chainFn: async ({ messages, tools }) => {
//     return model.bindTools(tools).stream(messages);
//     // or optionally enable strict mode
//     // return model.bindTools(tools, { strict: true }).stream(messages);
//   }
// });

// 创建 OpenAI 客户端，指向后端的 /chat/completions 端点
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  // baseURL: 'https://api.moonshot.cn/v1',
  baseURL: 'http://127.0.0.1:50020/api/taosha/v1/agents',
  fetch: async (url, options) => {
    console.log('=== API Request ===');
    console.log('URL:', url);
    if (options && options.body && typeof options.body === 'string') {
      const body = JSON.parse(options.body);
      console.log('Body:', JSON.stringify(body, null, 2));
    }
    const response = await fetch(url, options);
    console.log('Response status:', response.status);
    return response;
  }
});

// 创建 OpenAI 适配器
const llmAdapter = new OpenAIAdapter({
  openai,
  model: "kimi-k2-0905-preview",
  keepSystemRole: true,
});

const runtime = new CopilotRuntime();

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter: llmAdapter,
    endpoint: '/api/copilotkit',
  });

  return handleRequest(req);
};