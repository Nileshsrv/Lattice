declare module "plotly.js-basic-dist-min";
declare module "katex" {
  const katex: {
    renderToString(
      latex: string,
      options?: { displayMode?: boolean; throwOnError?: boolean }
    ): string;
  };
  export default katex;
}
