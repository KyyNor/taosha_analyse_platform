import api from "../api";

const BASE_PATH = "/common-services";

// OCR识别模式
export type OCRMode = "text" | "formula" | "table" | "json";

// 图片预处理信息
export interface ImagePreprocessInfo {
  original_size: [number, number];
  processed_size: [number, number];
  image_type: string;
  resized: boolean;
}

// OCR识别结果
export interface OCRImageData {
  success: boolean;
  result: string;
  mode: OCRMode;
  preprocess?: ImagePreprocessInfo;
  json_result?: Record<string, any>;
}

// PDF单页识别结果
export interface PDFPageResult {
  page: number;
  result: string;
  preprocess: {
    page_size: [number, number];
    dpi: number;
  };
}

// PDF识别结果
export interface PDFImageData {
  success: boolean;
  mode: OCRMode;
  total_pages: number;
  pages: PDFPageResult[];
  preprocess: {
    total_pages: number;
  };
}

// API响应包装
export interface OCRResult<T = OCRImageData | PDFImageData> {
  success: boolean;
  data: T;
  message: string;
}

// 健康检查结果
export interface HealthCheckResult {
  success: boolean;
  data: {
    status: "running" | "unavailable" | "error";
    base_url?: string;
    error?: string;
  };
  message: string;
}

export const commonServices = {
  // 图片OCR识别
  async ocrRecognize(
    file: File,
    mode: OCRMode = "text",
    jsonSchema?: string,
    apiKey?: string
  ): Promise<OCRResult<OCRImageData>> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", mode);
    if (jsonSchema) {
      formData.append("json_schema", jsonSchema);
    }
    if (apiKey) {
      formData.append("api_key", apiKey);
    }

    const response = await api.post(`${BASE_PATH}/ocr/recognize`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  // PDF OCR识别
  async ocrParsePDF(
    file: File,
    mode: OCRMode = "text",
    jsonSchema?: string,
    apiKey?: string
  ): Promise<OCRResult<PDFImageData>> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", mode);
    if (jsonSchema) {
      formData.append("json_schema", jsonSchema);
    }
    if (apiKey) {
      formData.append("api_key", apiKey);
    }

    const response = await api.post(`${BASE_PATH}/ocr/parse_pdf`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  // OCR服务健康检查
  async ocrHealthCheck(apiKey?: string): Promise<HealthCheckResult> {
    const params = apiKey ? { api_key: apiKey } : {};
    const response = await api.get(`${BASE_PATH}/ocr/health`, { params });
    return response.data;
  },
};

export default commonServices;
