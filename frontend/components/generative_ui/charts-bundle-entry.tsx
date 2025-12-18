/**
 * 图表组件打包入口
 * 将 Recharts 组件打包为独立 JS 文件供 HTML 报告使用
 *
 * 使用方式:
 *   npm run build:charts
 *
 * 输出文件:
 *   ../backend/services/agents/report/static/charts.bundle.js
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { LineChart, LineChartProps } from './LineChart';
import { BarChart, BarChartProps } from './BarChart';
import { PieChart, PieChartProps } from './PieChart';
import { TreemapChart, TreemapChartProps } from './TreemapChart';

// 图表组件注册表
const CHART_COMPONENTS: Record<string, React.FC<any>> = {
  line: LineChart,
  bar: BarChart,
  pie: PieChart,
  treemap: TreemapChart,
};

// 已渲染的 React 根节点
const renderedRoots: Map<string, ReactDOM.Root> = new Map();

/**
 * 淘沙图表库全局命名空间
 */
export const TaoshaCharts = {
  /**
   * 渲染单个图表
   * @param containerId 容器元素 ID
   * @param chartConfig 图表配置
   */
  render(containerId: string, chartConfig: any) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`TaoshaCharts: 容器不存在: ${containerId}`);
      return;
    }

    const chartType = chartConfig.chart_type || chartConfig.chartType;
    const ChartComponent = CHART_COMPONENTS[chartType];

    if (!ChartComponent) {
      console.error(`TaoshaCharts: 不支持的图表类型: ${chartType}`);
      console.log('支持的类型:', Object.keys(CHART_COMPONENTS));
      return;
    }

    try {
      // 如果已有根节点，先卸载
      if (renderedRoots.has(containerId)) {
        renderedRoots.get(containerId)?.unmount();
      }

      // 创建新的根节点并渲染
      const root = ReactDOM.createRoot(container);
      root.render(React.createElement(ChartComponent, chartConfig));
      renderedRoots.set(containerId, root);

      console.log(`TaoshaCharts: 已渲染 ${chartType} 图表到 #${containerId}`);
    } catch (error) {
      console.error(`TaoshaCharts: 渲染失败:`, error);
    }
  },

  /**
   * 批量渲染图表
   * @param chartsConfig 图表配置数组
   */
  renderAll(chartsConfig: any[]) {
    if (!Array.isArray(chartsConfig)) {
      console.error('TaoshaCharts: chartsConfig 必须是数组');
      return;
    }

    chartsConfig.forEach((config, index) => {
      const containerId = config.containerId || config.container_id || `chart-${index}`;
      this.render(containerId, config);
    });
  },

  /**
   * 从 DOM 属性自动渲染
   * 查找所有带有 data-chart-config 属性的元素并渲染
   */
  autoRender() {
    const elements = document.querySelectorAll('[data-chart-config]');
    elements.forEach((element, index) => {
      const configStr = element.getAttribute('data-chart-config');
      if (configStr) {
        try {
          const config = JSON.parse(configStr);
          const containerId = element.id || `auto-chart-${index}`;
          if (!element.id) {
            element.id = containerId;
          }
          this.render(containerId, config);
        } catch (error) {
          console.error('TaoshaCharts: 解析配置失败:', error);
        }
      }
    });
  },

  /**
   * 卸载图表
   * @param containerId 容器元素 ID
   */
  unmount(containerId: string) {
    if (renderedRoots.has(containerId)) {
      renderedRoots.get(containerId)?.unmount();
      renderedRoots.delete(containerId);
      console.log(`TaoshaCharts: 已卸载 #${containerId}`);
    }
  },

  /**
   * 卸载所有图表
   */
  unmountAll() {
    renderedRoots.forEach((root, id) => {
      root.unmount();
    });
    renderedRoots.clear();
    console.log('TaoshaCharts: 已卸载所有图表');
  },

  /**
   * 获取支持的图表类型
   */
  getSupportedTypes(): string[] {
    return Object.keys(CHART_COMPONENTS);
  },

  /**
   * 版本信息
   */
  version: '1.0.0',

  /**
   * 组件引用 (高级用法)
   */
  components: CHART_COMPONENTS,
};

// 挂载到全局对象
if (typeof window !== 'undefined') {
  (window as any).TaoshaCharts = TaoshaCharts;

  // DOM 加载完成后自动渲染
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      TaoshaCharts.autoRender();
    });
  } else {
    // DOM 已加载完成，延迟执行自动渲染
    setTimeout(() => TaoshaCharts.autoRender(), 0);
  }
}

// 导出类型
export type { LineChartProps, BarChartProps, PieChartProps, TreemapChartProps };
