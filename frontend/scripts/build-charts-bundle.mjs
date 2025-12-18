/**
 * 图表组件打包脚本
 * 将 Recharts 组件打包为独立的 JS 文件
 *
 * 使用方式:
 *   npm run build:charts
 *
 * 输出:
 *   ../backend/services/agents/report/static/charts.bundle.js
 */

import * as esbuild from 'esbuild';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(__dirname, '..');
const outputDir = path.resolve(frontendDir, '../backend/services/agents/report/static');

// 确保输出目录存在
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

console.log('🚀 开始打包图表组件...');
console.log(`📁 输入: ${path.join(frontendDir, 'components/generative_ui/charts-bundle-entry.tsx')}`);
console.log(`📁 输出: ${path.join(outputDir, 'charts.bundle.js')}`);

try {
  const result = await esbuild.build({
    entryPoints: [path.join(frontendDir, 'components/generative_ui/charts-bundle-entry.tsx')],
    bundle: true,
    minify: true,
    sourcemap: false,
    target: ['es2020'],
    format: 'iife',
    globalName: 'TaoshaCharts',
    outfile: path.join(outputDir, 'charts.bundle.js'),

    // React 和 ReactDOM 作为外部依赖，需要在 HTML 中单独引入
    // 如果需要完全独立的包，可以移除这两行
    // external: ['react', 'react-dom'],

    // 定义全局变量
    define: {
      'process.env.NODE_ENV': '"production"',
    },

    // 路径别名
    alias: {
      '@': frontendDir,
    },

    // 加载器配置
    loader: {
      '.tsx': 'tsx',
      '.ts': 'ts',
      '.js': 'js',
      '.jsx': 'jsx',
    },

    // 日志级别
    logLevel: 'info',
  });

  // 获取输出文件大小
  const outputFile = path.join(outputDir, 'charts.bundle.js');
  const stats = fs.statSync(outputFile);
  const fileSizeKB = (stats.size / 1024).toFixed(2);

  console.log('');
  console.log('✅ 打包完成!');
  console.log(`📦 文件大小: ${fileSizeKB} KB`);
  console.log(`📍 输出路径: ${outputFile}`);
  console.log('');
  console.log('使用方式:');
  console.log('  在 HTML 中添加:');
  console.log('  <script src="/static/js/charts.bundle.js"></script>');
  console.log('');
  console.log('  然后调用:');
  console.log('  TaoshaCharts.render("container-id", { chart_type: "line", data: [...] });');

} catch (error) {
  console.error('❌ 打包失败:', error);
  process.exit(1);
}
