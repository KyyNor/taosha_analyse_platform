declare module 'prismjs' {
  export const languages: Record<string, any>
  export const highlight: (code: string, grammar: any, language: string) => string
  export const highlightAll: () => void
  export default any
}

declare module 'prismjs/components/prism-sql' {
  export default any
}
