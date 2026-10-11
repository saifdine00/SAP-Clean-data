"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  getSession, getSessionStatus, bulkAcceptHighConfidence,
  SessionDetail, Anomaly
} from "@/lib/api";
import AnomalyTable from "@/components/AnomalyTable";
import ValidationReport from "@/components/ValidationReport";
import { cn, formatDate } from "@/lib/utils";
import {
  ArrowLeft, RefreshCw, Loader2, CheckCircle2, AlertTriangle,
  BarChart3, Zap, FileText
} from "lucide-react";
import Link from "next/link";

type Tab = "anomalies" | "report";

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("anomalies");
  const [bulkLoading, setBulkLoading] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const fetchSession = useCallback(async () => {
    try {
      const res = await getSession(sessionId);
      setSession(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  // Poll while analyzing
  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  useEffect(() => {
    if (!session) return;
    if (session.status === "analyzing") {
      pollingRef.current = setInterval(async () => {
        const res = await getSessionStatus(sessionId);
        if (res.data.status !== "analyzing") {
          clearInterval(pollingRef.current!);
          fetchSession();
        }
      }, 2500);
    }
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [session?.status, sessionId, fetchSession]);

  const handleUpdate = useCallback((id: string, status: string, correctedValue?: string) => {
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        anomalies: prev.anomalies.map((a) =>
          a.id === id
            ? { ...a, status: status as Anomaly["status"], corrected_value: correctedValue ?? a.corrected_value }
            : a
        ),
      };
    });
  }, []);

  const handleBulkAccept = async () => {
    setBulkLoading(true);
    try {
      await bulkAcceptHighConfidence(sessionId, 0.8);
      await fetchSession();
    } catch (e) {
      console.error(e);
    } finally {
      setBulkLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-indigo-400 mx-auto mb-4" />
          <p className="text-slate-400">Chargement de la session...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-4" />
          <p className="text-slate-300 font-semibold mb-2">Session introuvable</p>
          <Link href="/" className="btn-primary">← Retour à l'accueil</Link>
        </div>
      </div>
    );
  }

  const pendingCount = session.anomalies.filter((a) => a.status === "pending").length;
  const highConfCount = session.anomalies.filter(
    (a) => a.status === "pending" && a.confidence >= 0.8 && a.suggested_value
  ).length;

  return (
    <div className="min-h-screen px-4 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 gap-4 flex-wrap">
          <div className="flex items-start gap-4">
            <Link href="/" className="btn-ghost mt-1 p-2">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-xl font-bold text-slate-100 truncate max-w-lg">
                  {session.filename}
                </h1>
                <StatusBadge status={session.status} />
              </div>
              <p className="text-xs text-slate-500">
                Session {session.id.slice(0, 8)}... ·{" "}
                {session.total_rows.toLocaleString("fr-FR")} lignes ·{" "}
                {formatDate(session.created_at)} ·{" "}
                Format : {session.original_format.toUpperCase()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchSession}
              className="btn-ghost p-2"
              title="Actualiser"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            {highConfCount > 0 && (
              <button
                onClick={handleBulkAccept}
                disabled={bulkLoading}
                className="btn-primary text-sm"
                id="bulk-accept-btn"
              >
                {bulkLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4" />
                )}
                Accepter {highConfCount} correction{highConfCount > 1 ? "s" : ""} (≥80%)
              </button>
            )}
          </div>
        </div>

        {/* Analyzing state */}
        {session.status === "analyzing" && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 mb-6 flex items-center gap-4 border border-yellow-500/20"
          >
            <div className="w-10 h-10 rounded-xl bg-yellow-500/20 flex items-center justify-center flex-shrink-0">
              <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />
            </div>
            <div>
              <p className="text-sm font-semibold text-yellow-300">Analyse en cours...</p>
              <p className="text-xs text-slate-500">Détection des anomalies sur {session.total_rows.toLocaleString()} lignes</p>
            </div>
          </motion.div>
        )}

        {/* Quick stats */}
        {session.summary && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <StatCard label="Anomalies totales" value={session.summary.total_anomalies} icon="⚠️" />
            <StatCard label="En attente" value={pendingCount} icon="⏳" />
            <StatCard
              label="Lignes impactées"
              value={session.summary.rows_with_issues}
              icon="📋"
            />
            <StatCard
              label="Prêtes pour SAP"
              value={session.total_rows - session.summary.rows_with_issues}
              icon="✅"
              green
            />
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 mb-6 p-1 glass-card-static rounded-xl w-fit">
          <button
            onClick={() => setTab("anomalies")}
            className={cn(
              "px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2",
              tab === "anomalies"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            Anomalies
            {session.anomalies.length > 0 && (
              <span className={cn(
                "text-xs px-1.5 py-0.5 rounded-full",
                tab === "anomalies" ? "bg-white/20" : "bg-white/10 text-slate-400"
              )}>
                {session.anomalies.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setTab("report")}
            className={cn(
              "px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2",
              tab === "report"
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            Rapport & Export
          </button>
        </div>

        {/* Content */}
        {tab === "anomalies" ? (
          session.status === "ready" || session.anomalies.length > 0 ? (
            session.anomalies.length === 0 ? (
              <div className="glass-card p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
                <p className="text-lg font-semibold text-slate-200 mb-2">
                  Aucune anomalie détectée 🎉
                </p>
                <p className="text-slate-500 text-sm">
                  Vos données sont prêtes pour l'import SAP.
                </p>
              </div>
            ) : (
              <AnomalyTable anomalies={session.anomalies} onUpdate={handleUpdate} />
            )
          ) : (
            <div className="glass-card p-12 text-center text-slate-500">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-slate-600" />
              Analyse en attente...
            </div>
          )
        ) : (
          <ValidationReport session={session} />
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const configs: Record<string, { label: string; className: string }> = {
    pending: { label: "En attente", className: "bg-slate-500/20 text-slate-400 border-slate-500/30" },
    analyzing: { label: "Analyse...", className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30 animate-pulse" },
    ready: { label: "Prêt", className: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
    exported: { label: "Exporté", className: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  };
  const c = configs[status] || configs.pending;
  return <span className={cn("badge text-[11px]", c.className)}>{c.label}</span>;
}

function StatCard({
  label, value, icon, green,
}: {
  label: string; value: number; icon: string; green?: boolean;
}) {
  return (
    <div className="glass-card p-4">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{icon}</span>
      </div>
      <p className={cn("text-xl font-bold", green ? "text-emerald-400" : "text-slate-100")}>
        {value.toLocaleString("fr-FR")}
      </p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
    </div>
  );
}
