import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
    rules: {
      // TypeScript 相关 - 对于迁移项目适当放宽
      "@typescript-eslint/no-unused-vars": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-non-null-assertion": "warn",

      // React 相关
      "react-hooks/exhaustive-deps": "warn",
      "react/no-unescaped-entities": "warn",

      // 通用规则 - 放宽对迁移项目的要求
      "no-unused-vars": "warn",
      "prefer-const": "warn",

      // 导入相关 - 允许匿名默认导出（迁移阶段）
      "import/no-anonymous-default-export": "warn",

      // Next.js 相关
      "@next/next/no-img-element": "warn",
    },
  },
];

export default eslintConfig;
