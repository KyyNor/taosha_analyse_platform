/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

declare module 'plotly.js-dist' {
  import * as Plotly from 'plotly.js'
  export = Plotly
}