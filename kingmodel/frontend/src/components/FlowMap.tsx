import { ArrowRight } from "lucide-react";
import type { DashboardData } from "../types";

export function FlowMap({ data }: { data: DashboardData }) {
  const primary = data.mainlines[0];
  const secondary = data.mainlines[1];
  return <div className="flow-map">
    <div className="flow-source"><small>资金流出</small>{data.negative.slice(0, 3).map((item) => <span key={item.name}>{item.name} {item.change.toFixed(2)}%</span>)}</div>
    <div className="flow-arrow"><ArrowRight size={24} /><i /></div>
    <div className="flow-primary"><small>{primary?.role}</small><strong>{primary?.name}</strong><b>{primary?.score}</b><div>{primary?.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></div>
    <div className="flow-branch"><ArrowRight size={20} /></div>
    <div className="flow-secondary"><small>{secondary?.role}</small><strong>{secondary?.name}</strong><b>{secondary?.score}</b></div>
  </div>;
}
