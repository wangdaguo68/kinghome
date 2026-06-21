import type { CSSProperties } from "react";

export function ScoreGauge({ label, value, tone }: { label: string; value: number; tone: "red" | "green" | "amber" | "blue" }) {
  return <div className={`score-gauge tone-${tone}`} style={{ "--score": `${value * 3.6}deg` } as CSSProperties}>
    <div className="score-dial"><strong>{value}</strong></div><span>{label}</span>
  </div>;
}
