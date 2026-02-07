import api from "../api";

const BASE_PATH = "/common-services";

export interface OCRResult {
  success: boolean;
  data: any;
  message: string;
}

export const commonServices = {
  // OCR识别
  async ocrRecognize(formData: FormData): Promise<OCRResult> {
    const response = await api.post(`${BASE_PATH}/ocr/recognize`, formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },
};

export default commonServices;
