"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { listSessions, SessionSummary } from "@/lib/api";
import { formatDate, cn } from "@/lib/utils";
import FileUploader from "@/components/FileUploader";
import { History, ArrowRight, Loader2, Database, Shield, Zap, Sparkles } from "lucide-react";
import Link from "next/link";

const features = [
  {
    icon: <Database className="w-5 h-5" />,
    title: "Multi-format",
    desc: "Excel, CSV, JSON, copier-coller",
    color: "from-blue-500/20 to-indigo-500/20 border-blue-500/20",
    iconColor: "text-blue-400",
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: "15+ règles SAP",
    desc: "SIRET, IBAN, codes SAP, longueurs",
    color: "from-emerald-500/20 to-teal-500/20 border-emerald-500/20",
    iconColor: "text-emerald-400",
  },
  {
    icon: <Sparkles className="w-5 h-5" />,
    title: "IA Gemini",
    desc: "Suggestions intelligentes via LLM",
    color: "from-purple-500/20 to-pink-500/20 border-purple-500/20",
    iconColor: "text-purple-400",
  },
  {
    icon: <Zap className="w-5 h-5" />,
    title: "Export propre",
    desc: "CSV, Excel, rapport PDF",
    color: "from-orange-500/20 to-yellow-500/20 border-orange-500/20",
    iconColor: "text-orange-400",
  },
];

const statusColors: Record<string, string> = {
  pending: "text-slate-400",
  analyzing: "text-yellow-400",
  ready: "text-emerald-400",
  exported: "text-blue-400",
};
const statusDots: Record<string, string> = {
  pending: "bg-slate-400",
  analyzing: "bg-yellow-400 animate-pulse",
  ready: "bg-emerald-400",
  exported: "bg-blue-400",
};
const statusLabels: Record<string, string> = {
  pending: "En attente",
  analyzing: "Analyse...",
  ready: "Prêt",
  exported: "Exporté",
};

export default function HomePage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(true);

  useEffect(() => {
    listSessions()
      .then((r) => setSessions(r.data))
      .catch(() => {})
      .finally(() => setLoadingSessions(false));
  }, []);

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-5xl mx-auto">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-card-static border border-indigo-500/20 text-indigo-300 text-xs font-medium mb-6">
            <Sparkles className="w-3 h-3" />
            Propulsé par Gemini 2.0 Flash
          </div>
          <h1 className="text-5xl font-extrabold mb-4 leading-tight">
            <span className="gradient-text">SAP Data Cleaner</span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Nettoyez et validez vos données avant l'import SAP S/4HANA.
            Détection automatique des anomalies, corrections IA, export prêt à l'import.
          </p>
        </motion.div>

        {/* Feature pills */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-12"
        >
          {features.map((f, i) => (
            <div key={i} className={cn("glass-card p-4 border bg-gradient-to-br", f.color)}>
              <div className={cn("mb-2", f.iconColor)}>{f.icon}</div>
              <p className="text-sm font-semibold text-slate-200">{f.title}</p>
              <p className="text-xs text-slate-500">{f.desc}</p>
            </div>
          ))}
        </motion.div>

        {/* Upload card */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="glass-card p-8 mb-10"
        >
          <h2 className="text-lg font-bold text-slate-200 mb-6 flex items-center gap-2">
            <span className="w-6 h-6 rounded-md bg-indigo-500/20 flex items-center justify-center text-indigo-400 text-xs font-bold">1</span>
            Importer vos données
          </h2>
          <FileUploader />
        </motion.div>

        {/* Session history */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="glass-card p-6"
        >
          <h2 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2">
            <History className="w-4 h-4 text-slate-500" />
            Sessions récentes
          </h2>

          {loadingSessions ? (
            <div className="flex items-center gap-3 py-8 justify-center">
              <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
              <span className="text-sm text-slate-500">Chargement...</span>
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-slate-600 text-sm text-center py-8">
              Aucune session enregistrée. Importez un fichier pour commencer.
            </p>
          ) : (
            <div className="space-y-2">
              {sessions.map((s) => (
                <Link
                  key={s.id}
                  href={`/session/${s.id}`}
                  className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/[0.04] transition-all group"
                >
                  <div className={cn("w-2 h-2 rounded-full flex-shrink-0", statusDots[s.status] || "bg-slate-400")} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-200 truncate">{s.filename}</p>
                    <p className="text-xs text-slate-500">
                      {s.total_rows.toLocaleString("fr-FR")} lignes · {formatDate(s.created_at)}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className={cn("text-xs font-medium", statusColors[s.status])}>
                      {statusLabels[s.status] || s.status}
                    </p>
                    {s.summary?.total_anomalies !== undefined && (
                      <p className="text-xs text-slate-600">
                        {s.summary.total_anomalies} anomalie{s.summary.total_anomalies > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
                </Link>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
