"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2, XCircle, Pencil, Sparkles, ChevronDown, ChevronUp,
  Filter, Loader2, RotateCcw
} from "lucide-react";
import { Anomaly, applyCorrection, getLLMSuggestion, LLMSuggestion } from "@/lib/api";
import {
  ANOMALY_TYPE_LABELS, ANOMALY_TYPE_COLORS, getConfidenceColor, getConfidenceLabel, cn
} from "@/lib/utils";

interface AnomalyTableProps {
  anomalies: Anomaly[];
  onUpdate: (id: string, status: string, correctedValue?: string) => void;
}

type FilterType = "all" | string;

const PAGE_SIZE = 25;

export default function AnomalyTable({ anomalies, onUpdate }: AnomalyTableProps) {
  const [filterType, setFilterType] = useState<FilterType>("all");
  const [filterStatus, setFilterStatus] = useState<"all" | "pending" | "accepted" | "rejected" | "manual">("all");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [llmData, setLlmData] = useState<Record<string, LLMSuggestion>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  // Get unique anomaly types for filter
  const anomalyTypes = Array.from(new Set(anomalies.map((a) => a.anomaly_type)));

  const filtered = anomalies.filter((a) => {
    if (filterType !== "all" && a.anomaly_type !== filterType) return false;
    if (filterStatus !== "all" && a.status !== filterStatus) return false;
    return true;
  });

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleAction = useCallback(async (
    anomaly: Anomaly,
    action: "accept" | "reject" | "manual",
    manualValue?: string
  ) => {
    setLoadingId(anomaly.id);
    try {
      await applyCorrection(anomaly.id, action, manualValue);
      onUpdate(anomaly.id, action === "accept" ? "accepted" : action === "reject" ? "rejected" : "manual", manualValue || anomaly.suggested_value || undefined);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingId(null);
      setEditingId(null);
    }
  }, [onUpdate]);

  const handleLLM = useCallback(async (anomaly: Anomaly) => {
    setLoadingId(anomaly.id);
    try {
      const res = await getLLMSuggestion(anomaly.id);
      setLlmData((prev) => ({ ...prev, [anomaly.id]: res.data }));
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingId(null);
    }
  }, []);

  const startEdit = (anomaly: Anomaly) => {
    setEditingId(anomaly.id);
    setEditValue(anomaly.suggested_value || anomaly.original_value || "");
  };

  const statusColors: Record<string, string> = {
    pending: "bg-slate-500/15 text-slate-400 border-slate-500/25",
    accepted: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25",
    rejected: "bg-red-500/15 text-red-400 border-red-500/25",
    manual: "bg-blue-500/15 text-blue-400 border-blue-500/25",
  };
  const statusLabels: Record<string, string> = {
    pending: "En attente",
    accepted: "Accepté",
    rejected: "Rejeté",
    manual: "Manuel",
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-2 text-slate-400">
          <Filter className="w-3.5 h-3.5" />
          <span className="text-xs font-medium uppercase tracking-wider">Filtres</span>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => { setFilterType("all"); setPage(0); }}
            className={cn("badge cursor-pointer transition-all",
              filterType === "all"
                ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/30"
                : "bg-white/5 text-slate-400 border-white/10 hover:border-white/20"
            )}
          >
            Tous ({anomalies.length})
          </button>
          {anomalyTypes.map((type) => (
            <button
              key={type}
              onClick={() => { setFilterType(type); setPage(0); }}
              className={cn("badge cursor-pointer transition-all",
                filterType === type
                  ? ANOMALY_TYPE_COLORS[type] || "bg-slate-500/20 text-slate-300 border-slate-500/30"
                  : "bg-white/5 text-slate-400 border-white/10 hover:border-white/20"
              )}
            >
              {ANOMALY_TYPE_LABELS[type] || type} ({anomalies.filter((a) => a.anomaly_type === type).length})
            </button>
          ))}
        </div>

        <div className="ml-auto flex gap-2">
          {(["all", "pending", "accepted", "rejected", "manual"] as const).map((s) => (
            <button
              key={s}
              onClick={() => { setFilterStatus(s); setPage(0); }}
              className={cn("btn-ghost text-xs py-1.5 px-3",
                filterStatus === s && "bg-white/8 text-slate-200 border-white/20"
              )}
            >
              {s === "all" ? "Tous" : statusLabels[s]}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="glass-card-static overflow-hidden">
        <div className="overflow-x-auto" style={{ maxHeight: "65vh" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th className="w-14">Ligne</th>
                <th>Colonne</th>
                <th>Type</th>
                <th>Valeur originale</th>
                <th>Correction suggérée</th>
                <th className="w-24">Confiance</th>
                <th className="w-24">Statut</th>
                <th className="w-48">Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginated.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500">
                    Aucune anomalie pour ce filtre
                  </td>
                </tr>
              ) : (
                paginated.map((anomaly) => {
                  const llm = llmData[anomaly.id];
                  const isExpanded = expandedId === anomaly.id;
                  const isLoading = loadingId === anomaly.id;

                  return (
                    <>
                      <tr
                        key={anomaly.id}
                        className={cn(
                          "cursor-pointer",
                          isExpanded && "bg-white/[0.02]"
                        )}
                        onClick={() => setExpandedId(isExpanded ? null : anomaly.id)}
                      >
                        <td className="font-mono text-xs text-slate-500">
                          {anomaly.row_index + 1}
                        </td>
                        <td>
                          <span className="font-mono text-xs bg-white/5 px-2 py-0.5 rounded">
                            {anomaly.column_name}
                          </span>
                        </td>
                        <td>
                          <span className={cn("badge text-[10px]", ANOMALY_TYPE_COLORS[anomaly.anomaly_type] || "bg-slate-500/20 text-slate-300 border-slate-500/30")}>
                            {ANOMALY_TYPE_LABELS[anomaly.anomaly_type] || anomaly.anomaly_type}
                          </span>
                        </td>
                        <td>
                          <span className="font-mono text-xs text-red-300/80 bg-red-500/5 px-2 py-0.5 rounded max-w-[120px] inline-block truncate" title={anomaly.original_value || ""}>
                            {anomaly.original_value || <em className="text-slate-600">vide</em>}
                          </span>
                        </td>
                        <td>
                          {editingId === anomaly.id ? (
                            <input
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onClick={(e) => e.stopPropagation()}
                              autoFocus
                              className="w-full bg-white/5 border border-indigo-500/50 rounded px-2 py-1 text-xs font-mono text-slate-200 focus:outline-none"
                            />
                          ) : (
                            <span className={cn(
                              "font-mono text-xs px-2 py-0.5 rounded max-w-[120px] inline-block truncate",
                              anomaly.suggested_value
                                ? "text-emerald-300/80 bg-emerald-500/5"
                                : "text-slate-600 italic"
                            )} title={anomaly.suggested_value || ""}>
                              {anomaly.suggested_value || (llm?.suggested_value) || "—"}
                            </span>
                          )}
                        </td>
                        <td>
                          <span className={cn("text-xs font-semibold", getConfidenceColor(anomaly.confidence))}>
                            {Math.round(anomaly.confidence * 100)}%
                            <span className="text-slate-600 font-normal ml-1">
                              {getConfidenceLabel(anomaly.confidence)}
                            </span>
                          </span>
                        </td>
                        <td>
                          <span className={cn("badge text-[10px]", statusColors[anomaly.status])}>
                            {statusLabels[anomaly.status]}
                          </span>
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {isLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
                          ) : anomaly.status === "pending" ? (
                            <div className="flex items-center gap-1">
                              {editingId === anomaly.id ? (
                                <>
                                  <button
                                    id={`save-edit-${anomaly.id}`}
                                    onClick={() => handleAction(anomaly, "manual", editValue)}
                                    className="p-1.5 rounded-md bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-400 transition-colors"
                                    title="Sauvegarder"
                                  >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    onClick={() => setEditingId(null)}
                                    className="p-1.5 rounded-md hover:bg-white/5 text-slate-400 transition-colors"
                                    title="Annuler"
                                  >
                                    <RotateCcw className="w-3.5 h-3.5" />
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    id={`accept-${anomaly.id}`}
                                    onClick={() => handleAction(anomaly, "accept")}
                                    className="p-1.5 rounded-md bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 transition-colors"
                                    title="Accepter"
                                    disabled={!anomaly.suggested_value}
                                  >
                                    <CheckCircle2 className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    id={`reject-${anomaly.id}`}
                                    onClick={() => handleAction(anomaly, "reject")}
                                    className="p-1.5 rounded-md bg-red-500/15 hover:bg-red-500/25 text-red-400 transition-colors"
                                    title="Rejeter"
                                  >
                                    <XCircle className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    id={`edit-${anomaly.id}`}
                                    onClick={() => startEdit(anomaly)}
                                    className="p-1.5 rounded-md bg-blue-500/15 hover:bg-blue-500/25 text-blue-400 transition-colors"
                                    title="Modifier manuellement"
                                  >
                                    <Pencil className="w-3.5 h-3.5" />
                                  </button>
                                  <button
                                    id={`llm-${anomaly.id}`}
                                    onClick={() => handleLLM(anomaly)}
                                    className="p-1.5 rounded-md bg-purple-500/15 hover:bg-purple-500/25 text-purple-400 transition-colors"
                                    title="Suggestion IA (Gemini)"
                                  >
                                    <Sparkles className="w-3.5 h-3.5" />
                                  </button>
                                </>
                              )}
                            </div>
                          ) : (
                            <span className="text-xs text-slate-600">—</span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded detail row */}
                      {isExpanded && (
                        <tr key={`${anomaly.id}-expanded`} className="bg-white/[0.015]">
                          <td colSpan={8} className="px-4 pb-3 pt-0">
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: "auto" }}
                              className="border-t border-white/5 pt-3"
                            >
                              <p className="text-xs text-slate-400 mb-1 font-medium">Description de l'anomalie</p>
                              <p className="text-xs text-slate-300">{anomaly.message}</p>

                              {llm && (
                                <div className="mt-3 p-3 rounded-lg bg-purple-500/10 border border-purple-500/20">
                                  <p className="text-xs text-purple-300 font-semibold mb-1">
                                    ✨ Suggestion IA ({llm.source === "llm" ? "Gemini" : "Règles"}) · {Math.round(llm.confidence * 100)}% de confiance
                                  </p>
                                  <p className="text-xs text-slate-300">{llm.explanation}</p>
                                  {llm.alternatives && llm.alternatives.length > 0 && (
                                    <div className="flex gap-2 mt-2 flex-wrap">
                                      <span className="text-xs text-slate-500">Alternatives :</span>
                                      {llm.alternatives.map((alt, i) => (
                                        <span key={i} className="badge bg-white/5 border-white/10 text-slate-300 text-[10px]">
                                          {alt}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </motion.div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {pageCount > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500 text-xs">
            {filtered.length} anomalie{filtered.length > 1 ? "s" : ""} · Page {page + 1} / {pageCount}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-ghost text-xs py-1.5 px-3 disabled:opacity-40"
            >
              ← Précédent
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
              disabled={page >= pageCount - 1}
              className="btn-ghost text-xs py-1.5 px-3 disabled:opacity-40"
            >
              Suivant →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
