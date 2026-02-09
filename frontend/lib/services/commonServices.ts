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

// 文件输入模式
export type FileInputMode = "upload" | "url" | "local";

export const commonServices = {
  // 图片OCR识别
  async ocrRecognize(
    params: {
      mode: OCRMode;
      jsonSchema?: string;
      file?: File;
      fileUrl?: string;
      localPath?: string;
    }
  ): Promise<OCRResult<OCRImageData>> {
    const formData = new FormData();
    formData.append("mode", params.mode);

    if (params.jsonSchema) {
      formData.append("json_schema", params.jsonSchema);
    }

    // 根据输入模式添加不同的参数
    if (params.file) {
      formData.append("file", params.file);
    } else if (params.fileUrl) {
      formData.append("file_url", params.fileUrl);
    } else if (params.localPath) {
      formData.append("local_path", params.localPath);
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
    params: {
      mode: OCRMode;
      jsonSchema?: string;
      file?: File;
      fileUrl?: string;
      localPath?: string;
    }
  ): Promise<OCRResult<PDFImageData>> {
    const formData = new FormData();
    formData.append("mode", params.mode);

    if (params.jsonSchema) {
      formData.append("json_schema", params.jsonSchema);
    }

    // 根据输入模式添加不同的参数
    if (params.file) {
      formData.append("file", params.file);
    } else if (params.fileUrl) {
      formData.append("file_url", params.fileUrl);
    } else if (params.localPath) {
      formData.append("local_path", params.localPath);
    }

    const response = await api.post(`${BASE_PATH}/ocr/parse_pdf`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  // OCR服务健康检查
  async ocrHealthCheck(): Promise<HealthCheckResult> {
    const response = await api.get(`${BASE_PATH}/ocr/health`);
    return response.data;
  },
};

export default commonServices;
