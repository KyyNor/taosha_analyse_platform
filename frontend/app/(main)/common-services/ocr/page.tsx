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
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Copy, Download, Upload, Eye, X, FileText, Image as ImageIcon, CheckCircle, XCircle, Loader2, Link, FolderOpen, BookOpen, Code } from "lucide-react";
import { commonServices, type OCRMode, type OCRImageData, type PDFImageData, type FileInputMode } from "@/lib/services/commonServices";
import { toast } from "sonner";

export default function OCRPage() {
  const [fileInputMode, setFileInputMode] = useState<FileInputMode>("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [fileType, setFileType] = useState<"image" | "pdf" | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isHealthChecking, setIsHealthChecking] = useState(false);
  const [result, setResult] = useState<OCRImageData | PDFImageData | null>(null);
  const [mode, setMode] = useState<OCRMode>("text");
  const [jsonSchema, setJsonSchema] = useState("");
  const [healthStatus, setHealthStatus] = useState<"running" | "unavailable" | "error" | null>(null);
  const [showApiDocs, setShowApiDocs] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 从localStorage加载JSON Schema
  useEffect(() => {
    const savedSchema = localStorage.getItem("glm_ocr_json_schema");
    if (savedSchema) {
      setJsonSchema(savedSchema);
    }
  }, []);

  // 保存JSON Schema到localStorage
  useEffect(() => {
    if (jsonSchema) {
      localStorage.setItem("glm_ocr_json_schema", jsonSchema);
    }
  }, [jsonSchema]);

  // 健康检查
  const handleHealthCheck = async () => {
    setIsHealthChecking(true);
    try {
      const response = await commonServices.ocrHealthCheck();
      setHealthStatus(response.data.status);
      if (response.data.status === "running") {
        toast.success("OCR服务运行正常");
      } else {
        toast.warning(`OCR服务状态: ${response.data.status}`);
      }
    } catch (error: any) {
      setHealthStatus("error");
      toast.error("健康检查失败");
    } finally {
      setIsHealthChecking(false);
    }
  };

  // 处理文件选择
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);

      // 判断文件类型
      if (file.type === "application/pdf") {
        setFileType("pdf");
        setPreviewUrl(null);
      } else {
        setFileType("image");
        const url = URL.createObjectURL(file);
        setPreviewUrl(url);
      }

      // 清除之前的结果
      setResult(null);
    }
  };

  // 清除选中的文件
  const clearSelectedFile = () => {
    setSelectedFile(null);
    setFileType(null);
    setPreviewUrl(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // 处理识别
  const handleRecognize = async () => {
    if (mode === "json" && !jsonSchema) {
      toast.error("JSON模式需要配置JSON Schema");
      return;
    }

    // 验证输入
    if (fileInputMode === "upload") {
      if (!selectedFile) {
        toast.error("请先选择要识别的文件");
        return;
      }
    } else if (fileInputMode === "url") {
      if (!fileUrl) {
        toast.error("请输入文件URL");
        return;
      }
      // 简单的URL验证
      try {
        new URL(fileUrl);
      } catch {
        toast.error("请输入有效的URL");
        return;
      }
    } else if (fileInputMode === "local") {
      if (!localPath) {
        toast.error("请输入本地文件路径");
        return;
      }
    }

    setIsLoading(true);
    setResult(null);

    try {
      const params = {
        mode,
        jsonSchema: mode === "json" ? jsonSchema : undefined,
        file: fileInputMode === "upload" ? selectedFile! : undefined,
        fileUrl: fileInputMode === "url" ? fileUrl : undefined,
        localPath: fileInputMode === "local" ? localPath : undefined,
      };

      let response;
      if (selectedFile?.type === "application/pdf" || fileUrl?.toLowerCase().endsWith(".pdf")) {
        response = await commonServices.ocrParsePDF(params);
      } else {
        response = await commonServices.ocrRecognize(params);
      }

      if (response.success) {
        setResult(response.data);
        toast.success("识别成功");
      } else {
        toast.error(response.message || "识别失败");
      }
    } catch (error: any) {
      console.error("OCR识别错误:", error);
      toast.error(
        error.response?.data?.detail ||
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

    let text = "";
    if ("pages" in result) {
      // PDF结果
      text = result.pages.map(p => `--- 第 ${p.page} 页 ---\n${p.result}`).join("\n\n");
    } else if (result.json_result) {
      // JSON模式的图片结果
      text = JSON.stringify(result.json_result, null, 2);
    } else {
      // 普通文本模式
      text = result.result;
    }

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

    let text = "";
    let filename = "";
    if ("pages" in result) {
      // PDF结果
      text = result.pages.map(p => `--- 第 ${p.page} 页 ---\n${p.result}`).join("\n\n");
      filename = `ocr_result_pdf.txt`;
    } else if (result.json_result) {
      // JSON模式的图片结果
      text = JSON.stringify(result.json_result, null, 2);
      filename = `ocr_result.json`;
    } else {
      // 普通文本模式
      text = result.result;
      filename = `ocr_result_${mode}.txt`;
    }

    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success("下载成功");
  };

  // 获取模式描述
  const getModeDescription = (m: OCRMode) => {
    switch (m) {
      case "text":
        return "普通文本识别";
      case "formula":
        return "数学公式、化学式识别";
      case "table":
        return "表格结构及内容识别";
      case "json":
        return "结构化数据提取";
    }
  };

  // 获取输入模式描述
  const getInputModeDescription = (m: FileInputMode) => {
    switch (m) {
      case "upload":
        return "上传本地文件";
      case "url":
        return "输入文件远程URL";
      case "local":
        return "输入服务器本地文件路径（调试用）";
    }
  };

  return (
    <div className="flex-1 space-y-6 p-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">OCR识别</h1>
          <p className="text-muted-foreground">
            支持图片和PDF文件识别，提供多种识别模式
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog open={showApiDocs} onOpenChange={setShowApiDocs}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <BookOpen className="mr-2 h-4 w-4" />
                API文档
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[80vh]">
              <DialogHeader>
                <DialogTitle>OCR API 文档</DialogTitle>
                <DialogDescription>
                  提供 RESTful API 接口，支持图片和PDF文件的OCR文字识别
                </DialogDescription>
              </DialogHeader>
              <ScrollArea className="max-h-[60vh] pr-4">
                <div className="space-y-6">
                  {/* API端点 */}
                  <section>
                    <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                      <Code className="h-5 w-5" />
                      API端点
                    </h3>
                    <div className="space-y-3">
                      <Card>
                        <CardContent className="pt-4">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="default">POST</Badge>
                              <code className="text-sm bg-muted px-2 py-1 rounded">
                                /api/taosha/v1/common-services/ocr/recognize
                              </code>
                            </div>
                            <p className="text-sm text-muted-foreground">图片OCR识别接口</p>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-4">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="default">POST</Badge>
                              <code className="text-sm bg-muted px-2 py-1 rounded">
                                /api/taosha/v1/common-services/ocr/parse_pdf
                              </code>
                            </div>
                            <p className="text-sm text-muted-foreground">PDF OCR识别接口</p>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </section>

                  <Separator />

                  {/* 请求参数 */}
                  <section>
                    <h3 className="text-lg font-semibold mb-3">请求参数</h3>
                    <div className="space-y-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">文件输入（三选一）</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3 text-sm">
                            <div className="flex items-start gap-3">
                              <Badge variant="outline">file</Badge>
                              <div className="flex-1">
                                <p className="font-medium">上传文件</p>
                                <p className="text-muted-foreground">通过 FormData 上传图片或PDF文件</p>
                              </div>
                            </div>
                            <Separator />
                            <div className="flex items-start gap-3">
                              <Badge variant="outline">file_url</Badge>
                              <div className="flex-1">
                                <p className="font-medium">远程URL</p>
                                <p className="text-muted-foreground">服务器自动下载文件进行识别</p>
                              </div>
                            </div>
                            <Separator />
                            <div className="flex items-start gap-3">
                              <Badge variant="outline">local_path</Badge>
                              <div className="flex-1">
                                <p className="font-medium">本地路径</p>
                                <p className="text-muted-foreground">服务器本地文件路径（仅调试使用）</p>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">识别参数</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-3 text-sm">
                            <div className="flex items-start gap-3">
                              <Badge variant="secondary">mode</Badge>
                              <div className="flex-1">
                                <p className="font-medium">识别模式</p>
                                <p className="text-muted-foreground">可选值: text（默认）、formula、table、json</p>
                              </div>
                            </div>
                            <Separator />
                            <div className="flex items-start gap-3">
                              <Badge variant="secondary">json_schema</Badge>
                              <div className="flex-1">
                                <p className="font-medium">JSON Schema</p>
                                <p className="text-muted-foreground">当 mode=json 时必填，定义结构化数据提取模板</p>
                              </div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </section>

                  <Separator />

                  {/* 识别模式 */}
                  <section>
                    <h3 className="text-lg font-semibold mb-3">识别模式说明</h3>
                    <div className="grid grid-cols-2 gap-3">
                      <Card>
                        <CardContent className="pt-4">
                          <div className="space-y-1">
                            <Badge variant="outline">text</Badge>
                            <p className="text-sm font-medium">普通文本</p>
                            <p className="text-xs text-muted-foreground">识别文档、截图中的文字内容</p>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-4">
                          <div className="space-y-1">
                            <Badge variant="outline">formula</Badge>
                            <p className="text-sm font-medium">公式识别</p>
                            <p className="text-xs text-muted-foreground">识别数学公式、化学式等</p>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-4">
                          <div className="space-y-1">
                            <Badge variant="outline">table</Badge>
                            <p className="text-sm font-medium">表格识别</p>
                            <p className="text-xs text-muted-foreground">识别表格结构及内容</p>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardContent className="pt-4">
                          <div className="space-y-1">
                            <Badge variant="outline">json</Badge>
                            <p className="text-sm font-medium">结构化提取</p>
                            <p className="text-xs text-muted-foreground">按指定JSON格式提取信息</p>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </section>

                  <Separator />

                  {/* 响应格式 */}
                  <section>
                    <h3 className="text-lg font-semibold mb-3">响应格式</h3>
                    <Card>
                      <CardContent className="pt-4">
                        <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
{`{
  "success": true,
  "data": {
    "success": true,
    "result": "识别出的文字内容",
    "mode": "text",
    "preprocess": {
      "original_size": [1920, 1080],
      "processed_size": [1920, 1080],
      "image_type": "normal_photo",
      "resized": false
    }
  },
  "message": "识别成功"
}`}
                        </pre>
                      </CardContent>
                    </Card>
                  </section>

                  <Separator />

                  {/* 使用示例 */}
                  <section>
                    <h3 className="text-lg font-semibold mb-3">使用示例</h3>
                    <Card>
                      <CardContent className="pt-4">
                        <Tabs defaultValue="upload">
                          <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="upload">上传文件</TabsTrigger>
                            <TabsTrigger value="url">远程URL</TabsTrigger>
                            <TabsTrigger value="local">本地路径</TabsTrigger>
                          </TabsList>
                          <TabsContent value="upload" className="mt-4">
                            <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
{`curl -X POST \\
  http://localhost:50020/api/taosha/v1/common-services/ocr/recognize \\
  -F "file=@image.png" \\
  -F "mode=text"`}
                            </pre>
                          </TabsContent>
                          <TabsContent value="url" className="mt-4">
                            <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
{`curl -X POST \\
  http://localhost:50020/api/taosha/v1/common-services/ocr/recognize \\
  -F "file_url=https://example.com/image.png" \\
  -F "mode=text"`}
                            </pre>
                          </TabsContent>
                          <TabsContent value="local" className="mt-4">
                            <pre className="text-xs bg-muted p-4 rounded-lg overflow-x-auto">
{`curl -X POST \\
  http://localhost:50020/api/taosha/v1/common-services/ocr/recognize \\
  -F "local_path=/tmp/test.png" \\
  -F "mode=text"`}
                            </pre>
                          </TabsContent>
                        </Tabs>
                      </CardContent>
                    </Card>
                  </section>
                </div>
              </ScrollArea>
            </DialogContent>
          </Dialog>

          <Button
            variant="outline"
            onClick={handleHealthCheck}
            disabled={isHealthChecking}
          >
            {isHealthChecking ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                检查中
              </>
            ) : (
              <>
                {healthStatus === "running" ? (
                  <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                ) : healthStatus === "error" ? (
                  <XCircle className="mr-2 h-4 w-4 text-red-500" />
                ) : (
                  <Eye className="mr-2 h-4 w-4" />
                )}
                服务状态
              </>
            )}
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>识别配置</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* 文件输入模式选择 */}
            <div className="space-y-2">
              <Label>文件输入方式</Label>
              <Tabs value={fileInputMode} onValueChange={(v) => setFileInputMode(v as FileInputMode)}>
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="upload">
                    <Upload className="mr-2 h-4 w-4" />
                    上传文件
                  </TabsTrigger>
                  <TabsTrigger value="url">
                    <Link className="mr-2 h-4 w-4" />
                    远程URL
                  </TabsTrigger>
                  <TabsTrigger value="local">
                    <FolderOpen className="mr-2 h-4 w-4" />
                    本地路径
                  </TabsTrigger>
                </TabsList>
                <div className="mt-2">
                  <p className="text-sm text-muted-foreground">
                    {getInputModeDescription(fileInputMode)}
                  </p>
                </div>
              </Tabs>
            </div>

            <Separator />

            {/* 识别模式选择 */}
            <div className="space-y-2">
              <Label>识别模式</Label>
              <Tabs value={mode} onValueChange={(v) => setMode(v as OCRMode)}>
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="text">文本</TabsTrigger>
                  <TabsTrigger value="formula">公式</TabsTrigger>
                  <TabsTrigger value="table">表格</TabsTrigger>
                  <TabsTrigger value="json">结构化</TabsTrigger>
                </TabsList>
                <div className="mt-2">
                  <p className="text-sm text-muted-foreground">
                    {getModeDescription(mode)}
                  </p>
                </div>
              </Tabs>
            </div>

            {/* JSON Schema配置 */}
            {mode === "json" && (
              <>
                <Separator />
                <div className="space-y-2">
                  <Label htmlFor="json-schema">JSON Schema（结构化数据模板）</Label>
                  <Textarea
                    id="json-schema"
                    value={jsonSchema}
                    onChange={(e) => setJsonSchema(e.target.value)}
                    placeholder='{"id_number":"","name":"","date_of_birth":"","address":"","sex":""}'
                    rows={4}
                    className="font-mono text-sm"
                  />
                  <p className="text-sm text-muted-foreground">
                    定义要提取的字段及结构，OCR将按此模板返回结构化数据
                  </p>
                </div>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            {fileInputMode === "upload" && "文件上传"}
            {fileInputMode === "url" && "远程URL"}
            {fileInputMode === "local" && "本地文件路径"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {fileInputMode === "upload" && (
              <div className="border-2 border-dashed rounded-lg p-8 text-center">
                {selectedFile ? (
                  <div className="space-y-4">
                    {fileType === "image" && previewUrl ? (
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
                    ) : (
                      <div className="flex items-center justify-center space-x-3">
                        <FileText className="h-12 w-12 text-muted-foreground" />
                        <button
                          onClick={clearSelectedFile}
                          className="p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                    <div>
                      <p className="font-medium flex items-center justify-center gap-2">
                        {fileType === "image" ? (
                          <>
                            <ImageIcon className="h-4 w-4" />
                            {selectedFile.name}
                          </>
                        ) : (
                          <>
                            <FileText className="h-4 w-4" />
                            {selectedFile.name}
                          </>
                        )}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
                    <div className="space-y-2">
                      <p className="text-sm font-medium">点击或拖拽文件到此处</p>
                      <p className="text-xs text-muted-foreground">
                        支持 JPG、PNG、BMP、GIF、WEBP、TIFF 图片格式
                        <br />
                        支持 PDF 文档格式
                        <br />
                        文件大小不超过 200 MB
                      </p>
                    </div>
                    <Input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*,.pdf"
                      onChange={handleFileChange}
                      className="hidden"
                      id="file-input"
                    />
                    <Button asChild>
                      <label htmlFor="file-input">选择文件</label>
                    </Button>
                  </div>
                )}
              </div>
            )}

            {fileInputMode === "url" && (
              <div className="space-y-2">
                <Label htmlFor="file-url">文件URL</Label>
                <Input
                  id="file-url"
                  value={fileUrl}
                  onChange={(e) => setFileUrl(e.target.value)}
                  placeholder="https://example.com/image.png"
                />
                <p className="text-sm text-muted-foreground">
                  输入图片或PDF文件的完整URL地址
                </p>
              </div>
            )}

            {fileInputMode === "local" && (
              <div className="space-y-2">
                <Label htmlFor="local-path">本地文件路径</Label>
                <Input
                  id="local-path"
                  value={localPath}
                  onChange={(e) => setLocalPath(e.target.value)}
                  placeholder="/path/to/file.png"
                />
                <p className="text-sm text-muted-foreground">
                  输入服务器上的本地文件路径（仅用于调试）
                </p>
              </div>
            )}

            {(selectedFile || fileUrl || localPath) && (
              <div className="flex justify-end">
                <Button onClick={handleRecognize} disabled={isLoading}>
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      识别中...
                    </>
                  ) : (
                    "开始识别"
                  )}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>识别结果</CardTitle>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="outline">{mode}</Badge>
                {"pages" in result && (
                  <Badge variant="secondary">共 {result.total_pages} 页</Badge>
                )}
              </div>
            </div>
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
            <div className="rounded-lg border bg-card p-4 max-h-96 overflow-y-auto">
              {"pages" in result ? (
                // PDF结果
                <div className="space-y-4">
                  {result.pages.map((page) => (
                    <div key={page.page} className="border-b pb-4 last:border-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline">第 {page.page} 页</Badge>
                        <span className="text-xs text-muted-foreground">
                          DPI: {page.preprocess.dpi}
                        </span>
                      </div>
                      <pre className="whitespace-pre-wrap text-sm font-mono">
                        {page.result}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : result.json_result ? (
                // JSON模式结果
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {JSON.stringify(result.json_result, null, 2)}
                </pre>
              ) : (
                // 普通文本结果
                <pre className="whitespace-pre-wrap text-sm font-mono">
                  {result.result}
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
          - 支持三种文件输入方式：上传文件、远程URL、本地路径（调试）
          - 图片大小不超过 200 MB，支持 JPG、PNG、BMP、GIF、WEBP、TIFF 格式
          - PDF 文件大小不超过 200 MB，无页数限制
          - 识别结果将保留在当前会话中，刷新页面后会丢失
          - JSON 模式需要配置 JSON Schema 以定义提取的字段结构
          - 本地路径模式仅用于调试，请确保服务器有访问该文件的权限
        </AlertDescription>
      </Alert>
    </div>
  );
}
