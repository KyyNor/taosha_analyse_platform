"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Copy, Download, Upload, Eye, X } from "lucide-react";
import { commonServices, type OCRResult } from "@/lib/services/commonServices";
import { toast } from "sonner";

export default function OCRPage() {
  const [apiKey, setApiKey] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<OCRResult | null>(null);
  const [outputFormat, setOutputFormat] = useState<"json" | "markdown">("json");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 从localStorage加载API Key
  useEffect(() => {
    const savedKey = localStorage.getItem("glm_ocr_api_key");
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, []);

  // 保存API Key到localStorage
  useEffect(() => {
    if (apiKey) {
      localStorage.setItem("glm_ocr_api_key", apiKey);
    }
  }, [apiKey]);

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);

      // 生成预览URL
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);

      // 清除之前的结果
      setResult(null);
    }
  };

  // 清除选中的文件
  const clearSelectedFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // 处理识别
  const handleRecognize = async () => {
    if (!selectedFile) {
      toast.error("请先选择要识别的图片");
      return;
    }

    if (!apiKey) {
      toast.error("请输入API Key");
      return;
    }

    setIsLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("api_key", apiKey);
      formData.append("output_format", outputFormat);

      const response = await commonServices.ocrRecognize(formData);

      if (response.success) {
        setResult(response);
        toast.success("识别成功");
      } else {
        toast.error(response.message || "识别失败");
      }
    } catch (error: any) {
      console.error("OCR识别错误:", error);
      toast.error(
        error.response?.data?.message ||
          error.message ||
          "识别过程中发生错误"
      );
    } finally {
      setIsLoading(false);
    }
  };

  // 复制识别结果
  const handleCopyResult = () => {
    if (!result) return;

    const text =
      typeof result.data === "string" ? result.data : JSON.stringify(result.data, null, 2);

    navigator.clipboard
      .writeText(text)
      .then(() => {
        toast.success("已复制到剪贴板");
      })
      .catch((err) => {
        console.error("复制失败:", err);
        toast.error("复制失败");
      });
  };

  // 下载识别结果
  const handleDownloadResult = () => {
    if (!result) return;

    const text =
      typeof result.data === "string" ? result.data : JSON.stringify(result.data, null, 2);

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = `ocr_result.${
      outputFormat === "json" ? "json" : "md"
    }`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success("下载成功");
  };

  return (
    <div className="flex-1 space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">OCR识别</h1>
          <p className="text-muted-foreground">
            上传图片进行OCR识别，支持JSON和Markdown两种输出格式
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>API配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="api-key">GLM-OCR API Key</Label>
              <Input
                id="api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="请输入API Key"
              />
              <p className="text-sm text-muted-foreground">
                请输入您的GLM-OCR API Key，系统会记住您的密钥以便下次使用
              </p>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label htmlFor="output-format">输出格式</Label>
              <Tabs
                value={outputFormat}
                onValueChange={(value) =>
                  setOutputFormat(value as "json" | "markdown")
                }
              >
                <TabsList>
                  <TabsTrigger value="json">JSON格式</TabsTrigger>
                  <TabsTrigger value="markdown">Markdown格式</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>图片上传</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center">
              {selectedFile ? (
                <div className="space-y-4">
                  <div className="relative inline-block">
                    <img
                      src={previewUrl!}
                      alt="预览"
                      className="max-h-64 max-w-full object-contain rounded"
                    />
                    <button
                      onClick={clearSelectedFile}
                      className="absolute -top-2 -right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                  <div>
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
                  <div className="space-y-2">
                    <p className="text-sm font-medium">点击或拖拽图片到此处</p>
                    <p className="text-xs text-muted-foreground">
                      支持 JPG、PNG、BMP 格式，文件大小不超过 10 MB
                    </p>
                  </div>
                  <Input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-input"
                  />
                  <Button asChild>
                    <label htmlFor="file-input">选择图片</label>
                  </Button>
                </div>
              )}
            </div>

            {selectedFile && (
              <div className="flex justify-end">
                <Button onClick={handleRecognize} disabled={isLoading}>
                  {isLoading ? "识别中..." : "开始识别"}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>识别结果</CardTitle>
            <div className="flex space-x-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCopyResult}
              >
                <Copy className="mr-2 h-4 w-4" />
                复制
              </Button>
              <Button variant="secondary" size="sm" onClick={handleDownloadResult}>
                <Download className="mr-2 h-4 w-4" />
                下载
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border bg-card p-4">
              {typeof result.data === "string" ? (
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {result.data}
                </pre>
              ) : (
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <Alert>
        <Eye className="h-4 w-4" />
        <AlertTitle>注意事项</AlertTitle>
        <AlertDescription>
          - 请确保输入有效的GLM-OCR API Key
          - 图片大小不超过 10 MB
          - 支持的图片格式：JPG、PNG、BMP
          - 识别结果将保留在当前会话中，刷新页面后会丢失
        </AlertDescription>
      </Alert>
    </div>
  );
}
