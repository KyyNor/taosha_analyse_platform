/**
 * 天气卡片组件
 * 用于展示城市天气信息的生成式UI组件
 */
import React from 'react';
import { Cloud, Droplets, Wind, MapPin, Clock } from 'lucide-react';

export interface WeatherCardProps {
  province?: string;
  city: string;
  adcode?: string;
  weather: string;
  temperature: number;
  wind_direction?: string;
  wind_power?: string;
  humidity?: number;
  report_time?: string;
}

export interface WeatherCardState {
  state: 'loading' | 'success' | 'error';
  data?: WeatherCardProps;
  error?: string;
}

/**
 * 天气卡片组件 - 成功状态
 */
export const WeatherCard: React.FC<WeatherCardProps> = ({
  province,
  city,
  weather,
  temperature,
  wind_direction,
  wind_power,
  humidity,
  report_time,
}) => {
  // 根据天气状况选择图标颜色
  const getWeatherColor = (condition: string) => {
    if (condition.includes('晴')) return 'text-yellow-500';
    if (condition.includes('云')) return 'text-gray-400';
    if (condition.includes('雨')) return 'text-blue-500';
    if (condition.includes('雪')) return 'text-blue-300';
    return 'text-gray-500';
  };

  // 根据温度选择颜色
  const getTempColor = (temp: number) => {
    if (temp >= 30) return 'text-red-500';
    if (temp >= 20) return 'text-orange-500';
    if (temp >= 10) return 'text-green-500';
    return 'text-blue-500';
  };

  return (
    <div className="my-4 p-6 max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 transition-all hover:shadow-md">
      {/* 标题栏 */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <MapPin className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          <h3 className="text-xl font-bold text-gray-800 dark:text-gray-100">
            {city}
          </h3>
          {province && (
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {province}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Cloud className={`w-6 h-6 ${getWeatherColor(weather)}`} />
          <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm font-medium">
            {weather}
          </span>
        </div>
      </div>

      {/* 温度显示 */}
      <div className="flex items-end space-x-2 mb-6">
        <span className={`text-6xl font-bold ${getTempColor(temperature)}`}>
          {temperature}
        </span>
        <span className="text-3xl text-gray-500 dark:text-gray-400 mb-2">°C</span>
      </div>

      {/* 详细信息 */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        {humidity !== undefined && (
          <div className="flex items-center gap-2">
            <Droplets className="w-5 h-5 text-blue-500" />
            <div className="flex flex-col">
              <span className="text-xs text-gray-500 dark:text-gray-400">湿度</span>
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {humidity}%
              </span>
            </div>
          </div>
        )}

        {wind_direction && wind_power && (
          <div className="flex items-center gap-2">
            <Wind className="w-5 h-5 text-gray-500" />
            <div className="flex flex-col">
              <span className="text-xs text-gray-500 dark:text-gray-400">风力</span>
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                {wind_direction} {wind_power}级
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 报告时间 */}
      {report_time && (
        <div className="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <Clock className="w-4 h-4" />
          <span>更新于 {report_time}</span>
        </div>
      )}
    </div>
  );
};

/**
 * 天气卡片加载状态组件
 */
export const WeatherCardSkeleton: React.FC = () => {
  return (
    <div className="my-4 p-6 max-w-md bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-gray-300 dark:bg-gray-600 rounded"></div>
          <div className="h-6 w-24 bg-gray-300 dark:bg-gray-600 rounded"></div>
        </div>
        <div className="h-8 w-20 bg-gray-300 dark:bg-gray-600 rounded-full"></div>
      </div>

      <div className="flex items-end space-x-2 mb-6">
        <div className="h-16 w-32 bg-gray-300 dark:bg-gray-600 rounded"></div>
      </div>

      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="h-12 bg-gray-300 dark:bg-gray-600 rounded"></div>
        <div className="h-12 bg-gray-300 dark:bg-gray-600 rounded"></div>
      </div>
    </div>
  );
};

/**
 * 天气卡片错误状态组件
 */
export const WeatherCardError: React.FC<{ error: string; city?: string }> = ({
  error,
  city,
}) => {
  return (
    <div className="my-4 p-6 max-w-md bg-red-50 dark:bg-red-900/20 rounded-lg shadow-sm border border-red-200 dark:border-red-800">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
          <Cloud className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">
            获取天气失败
          </h3>
          {city && (
            <p className="text-sm text-red-600 dark:text-red-400">{city}</p>
          )}
        </div>
      </div>
      <p className="text-sm text-red-700 dark:text-red-300 mt-2">{error}</p>
    </div>
  );
};
