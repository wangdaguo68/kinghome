import { ArrowRight, CircleDot } from "lucide-react";
import type { DashboardData } from "../types";

export function FlowMap({ data }: { data: DashboardData }) {
  const graph = data.market_graph;
  if (!graph?.nodes?.length) {
    const primary = data.mainlines[0];
    const secondary = data.mainlines[1];
    return <div className="flow-map legacy">
      <div className="flow-source"><small>资金流出</small>{data.negative.slice(0, 3).map((item) => <span key={item.name}>{item.name} {item.change.toFixed(2)}%</span>)}</div>
      <div className="flow-arrow"><ArrowRight size={24} /><i /></div>
      <div className="flow-primary"><small>{primary?.role}</small><strong>{primary?.name}</strong><b>{primary?.score}</b><div>{primary?.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></div>
      <div className="flow-branch"><ArrowRight size={20} /></div>
      <div className="flow-secondary"><small>{secondary?.role}</small><strong>{secondary?.name}</strong><b>{secondary?.score}</b></div>
    </div>;
  }

  const columns = [
    { key: "negative", title: "负反馈", types: ["negative", "negative_stock"] },
    { key: "market", title: "市场状态", types: ["market", "capacity"] },
    { key: "sector", title: "正反馈/联动", types: ["mainline", "sector", "linkage"] },
    { key: "core", title: "核心/计划", types: ["leader", "capacity_core", "plan"] },
  ];
  const edgesByTarget = new Map<string, typeof graph.edges>();
  for (const edge of graph.edges) {
    const list = edgesByTarget.get(edge.target) ?? [];
    list.push(edge);
    edgesByTarget.set(edge.target, list);
  }

  return <div className="market-graph">
    {columns.map((column) => {
      const nodes = graph.nodes.filter((node) => column.types.includes(node.type));
      return <section key={column.key} className={`graph-column graph-${column.key}`}>
        <header>{column.title}<span>{nodes.length}</span></header>
        <div className="graph-node-stack">
          {nodes.map((node) => <article key={node.id} className={`graph-node node-${node.type}`}>
            <div className="graph-node-title"><CircleDot size={13} /><strong>{node.label}</strong><em>{Number(node.score || 0).toFixed(0)}</em></div>
            <p>{node.detail}</p>
            {(edgesByTarget.get(node.id) ?? []).slice(0, 2).map((edge) => <small key={`${edge.source}-${edge.target}-${edge.label}`} className={`edge-${edge.tone}`}><ArrowRight size={11} />{edge.label}</small>)}
          </article>)}
        </div>
      </section>;
    })}
  </div>;
}
