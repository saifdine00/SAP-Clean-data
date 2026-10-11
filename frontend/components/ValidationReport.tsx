"use client";

import { SessionDetail } from "@/lib/api";
import { exportCsv, exportXlsx, exportReportPdf } from "@/lib/api";
import { FileDown, FileText, BarChart3, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface ValidationReportProps {
  session: SessionDetail;
}

const COLORS = [
  "#ef4444", "#f97316", "#eab308", "#22c55e",
  "#3b82f6", "#8b5cf6", "#ec4899", "#14b8a6",
  "#f59e0b", "#6366f1",
];

export default function ValidationReport({ session }: ValidationReportProps) {
  const summary = session.summary;
  if (!summary) return null;

  const anomalyPieData = Object.entries(summary.anomalies_by_type || {})
    .map(([name, value]) => ({
      name: name.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      value,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const rowsOk = summary.total_rows - summary.rows_with_issues;
  const pctOk = summary.total_rows > 0 ? Math.round((rowsOk / summary.total_rows) * 100) : 0;

  const statCards = [
    {
      label: "Lignes totales",
      value: summary.total_rows,
      icon: <BarChart3 className="w-5 h-5" />,
      color: "text-slate-300",
      bg: "bg-slate-500/10",
    },
    {
      label: "Lignes avec problèmes",
      value: summary.rows_with_issues,
      icon: <AlertCircle className="w-5 h-5" />,
      color: "text-red-400",
      bg: "bg-red-500/10",
    },
    {
      label: "Prêtes pour SAP",
      value: rowsOk,
      icon: <CheckCircle2 className="w-5 h-5" />,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
    },
    {
      label: "Anomalies détectées",
      value: summary.total_anomalies,
      icon: <Clock className="w-5 h-5" />,
      color: "text-yellow-400",
      bg: "bg-yellow-500/10",
    },
  ];

  return (
    <div className="space-y-6 fade-in">
      {/* Summary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => (
          <div key={i} className="glass-card p-5">
            <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center mb-3", card.bg, card.color)}>
              {card.icon}
            </div>
            <p className="text-2xl font-bold text-white mb-0.5">{card.value.toLocaleString("fr-FR")}</p>
            <p className="text-xs text-slate-500">{card.label}</p>
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="glass-card p-6">
        <div className="flex justify-between items-center mb-3">
          <h3 className="text-sm font-semibold text-slate-200">Taux de préparation SAP</h3>
          <span className={cn("text-2xl font-bold", pctOk >= 80 ? "text-emerald-400" : pctOk >= 50 ? "text-yellow-400" : "text-red-400")}>
            {pctOk}%
          </span>
        </div>
        <div className="progress-bar h-3">
          <div
            className="h-full rounded-full transition-all duration-1000"
            style={{
              width: `${pctOk}%`,
              background: pctOk >= 80
                ? "linear-gradient(90deg, #10b981, #34d399)"
                : pctOk >= 50
                ? "linear-gradient(90deg, #f59e0b, #fbbf24)"
                : "linear-gradient(90deg, #ef4444, #f97316)",
            }}
          />
        </div>
        <p className="text-xs text-slate-500 mt-2">
          {rowsOk} ligne{rowsOk > 1 ? "s" : ""} prête{rowsOk > 1 ? "s" : ""} sur {summary.total_rows} pour l'import SAP
        </p>
      </div>

      {/* Pie chart + type breakdown */}
      {anomalyPieData.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-4">
          <div className="glass-card p-6">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Répartition des anomalies</h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={anomalyPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {anomalyPieData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#0d1424",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  labelStyle={{ color: "#94a3b8" }}
                  itemStyle={{ color: "#f1f5f9" }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "11px", color: "#94a3b8" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="glass-card p-6">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Détail par type</h3>
            <div className="space-y-2 overflow-y-auto" style={{ maxHeight: "220px" }}>
              {Object.entries(summary.anomalies_by_type || {})
                .sort(([, a], [, b]) => b - a)
                .map(([type, count], i) => (
                  <div key={type} className="flex items-center gap-3">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-xs text-slate-400 flex-1 truncate">
                      {type.replace(/_/g, " ")}
                    </span>
                    <span className="text-xs font-semibold text-slate-200">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {/* Export buttons */}
      <div className="glass-card p-6">
        <h3 className="text-sm font-semibold text-slate-200 mb-4">Exporter les données corrigées</h3>
        <div className="flex flex-wrap gap-3">
          <a
            href={exportCsv(session.id)}
            download
            id="export-csv-btn"
            className="btn-primary bg-gradient-to-r from-emerald-600 to-teal-600 shadow-emerald-500/20"
          >
            <FileDown className="w-4 h-4" />
            Télécharger CSV
          </a>
          <a
            href={exportXlsx(session.id)}
            download
            id="export-xlsx-btn"
            className="btn-primary bg-gradient-to-r from-green-600 to-emerald-600 shadow-green-500/20"
          >
            <FileDown className="w-4 h-4" />
            Télécharger Excel
          </a>
          <a
            href={exportReportPdf(session.id)}
            download
            id="export-pdf-btn"
            className="btn-primary bg-gradient-to-r from-rose-600 to-pink-600 shadow-rose-500/20"
          >
            <FileText className="w-4 h-4" />
            Rapport PDF
          </a>
        </div>
        <p className="text-xs text-slate-600 mt-3">
          Les corrections acceptées et manuelles sont appliquées · Les doublons acceptés sont supprimés
        </p>
      </div>
    </div>
  );
}
