import Plotly from "plotly.js-basic-dist-min";
import { useEffect, useRef, useState } from "react";

export interface SeriesSpec {
  x: number[];
  y: number[];
  name: string;
  mode?: string;
}

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function useThemeVersion(): string {
  const [theme, setTheme] = useState(
    document.documentElement.getAttribute("data-theme") ?? "dark"
  );
  useEffect(() => {
    const observer = new MutationObserver(() =>
      setTheme(document.documentElement.getAttribute("data-theme") ?? "dark")
    );
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);
  return theme;
}

export function Plot(props: {
  series: SeriesSpec[];
  xLabel: string;
  yLabel: string;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const theme = useThemeVersion();

  useEffect(() => {
    if (!ref.current) return;
    // Categorical slots are assigned in fixed order (validated palette), never cycled.
    const palette = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => cssVar(`--series-${i}`));
    const ink = cssVar("--text-secondary");
    const grid = cssVar("--plot-grid");
    const axis = cssVar("--plot-axis");
    const surface = cssVar("--plot-surface");

    const traces = props.series.map((s, i) => {
      const dense = s.x.length > 200;
      return {
        x: s.x,
        y: s.y,
        name: s.name,
        type: "scatter",
        mode: s.mode ?? "markers",
        marker: {
          size: dense ? 3.5 : 8,
          color: palette[i % palette.length],
          opacity: dense ? 0.75 : 1,
          line: dense ? undefined : { width: 2, color: surface },
        },
        line: { width: 2, color: palette[i % palette.length] },
        hovertemplate: `%{x:.5g}, %{y:.5g}<extra>${s.name}</extra>`,
      };
    });

    const axisStyle = {
      gridcolor: grid,
      zerolinecolor: grid,
      linecolor: axis,
      tickcolor: axis,
      ticks: "outside",
      ticklen: 4,
      tickfont: { size: 11, color: ink },
      title: { font: { size: 12, color: ink } },
      exponentformat: "power",
    };

    Plotly.newPlot(
      ref.current,
      traces,
      {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { family: "Inter, Segoe UI, system-ui, sans-serif", color: ink, size: 12 },
        margin: { t: props.series.length > 1 ? 34 : 14, r: 18, b: 46, l: 58 },
        xaxis: { ...axisStyle, title: { ...axisStyle.title, text: props.xLabel } },
        yaxis: { ...axisStyle, title: { ...axisStyle.title, text: props.yLabel } },
        showlegend: props.series.length > 1,
        legend: { orientation: "h", y: 1.12, x: 0, font: { size: 12, color: ink } },
        hovermode: "closest",
        hoverlabel: {
          bgcolor: cssVar("--bg-raised"),
          bordercolor: cssVar("--border-strong"),
          font: { color: cssVar("--text-primary"), size: 12 },
        },
        autosize: true,
      },
      { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] }
    );
    const node = ref.current;
    return () => {
      Plotly.purge(node);
    };
  }, [theme, JSON.stringify(props.series.map((s) => [s.name, s.x.length]))]);

  // Height lives in CSS: Plotly's responsive resize discards layout.height.
  return (
    <div className="plot-frame">
      <div ref={ref} style={{ height: props.height ?? 380, width: "100%" }} />
    </div>
  );
}
