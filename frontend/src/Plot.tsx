import Plotly from "plotly.js-basic-dist-min";
import { useEffect, useRef } from "react";

export interface SeriesSpec {
  x: number[];
  y: number[];
  name: string;
  mode?: string;
}

const AXIS_STYLE = {
  gridcolor: "rgba(255,255,255,0.08)",
  zerolinecolor: "rgba(255,255,255,0.15)",
  linecolor: "rgba(255,255,255,0.25)",
  tickfont: { size: 11 },
};

export function Plot(props: {
  series: SeriesSpec[];
  xLabel: string;
  yLabel: string;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const traces = props.series.map((s, i) => ({
      x: s.x,
      y: s.y,
      name: s.name,
      mode: s.mode ?? "markers",
      marker: { size: 3 },
      line: { width: 2 },
    }));
    Plotly.newPlot(
      ref.current,
      traces,
      {
        paper_bgcolor: "transparent",
        plot_bgcolor: "transparent",
        font: { color: "#e8ebef", size: 12 },
        margin: { t: 16, r: 16, b: 48, l: 60 },
        xaxis: { title: { text: props.xLabel }, exponentformat: "power", ...AXIS_STYLE },
        yaxis: { title: { text: props.yLabel }, ...AXIS_STYLE },
        legend: { orientation: "h", y: 1.08 },
        height: props.height ?? 380,
      },
      { displaylogo: false, responsive: true }
    );
    return () => {
      if (ref.current) Plotly.purge(ref.current);
    };
  }, [JSON.stringify(props.series.map((s) => [s.name, s.x.length]))]);
  return <div className="plot-frame" ref={ref} />;
}
