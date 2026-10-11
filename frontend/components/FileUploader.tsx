"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, X, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { uploadFile, uploadPaste, UploadResponse } from "@/lib/api";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = {
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.ms-excel": [".xls"],
  "text/csv": [".csv"],
  "application/json": [".json"],
};

type UploadState = "idle" | "uploading" | "success" | "error";

export default function FileUploader() {
  const router = useRouter();
  const [tab, setTab] = useState<"file" | "paste">("file");
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pasteText, setPasteText] = useState("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      setError(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    onDropRejected: (rejections) => {
      setError(rejections[0]?.errors[0]?.message || "Fichier refusé");
    },
  });

  const handleUpload = async () => {
    if (tab === "file" && !selectedFile) return;
    if (tab === "paste" && !pasteText.trim()) return;

    setUploadState("uploading");
    setError(null);
    setProgress(0);

    try {
      let res: UploadResponse;
      if (tab === "file") {
        const response = await uploadFile(selectedFile!, (pct) => setProgress(pct));
        res = response.data;
      } else {
        const response = await uploadPaste(pasteText);
        res = response.data;
      }
      setUploadState("success");
      setTimeout(() => router.push(`/session/${res.session_id}`), 800);
    } catch (err: any) {
      setUploadState("error");
      setError(err.response?.data?.detail || "Erreur lors du téléversement.");
    }
  };

  const resetFile = () => {
    setSelectedFile(null);
    setUploadState("idle");
    setError(null);
    setProgress(0);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 glass-card-static rounded-xl w-fit">
        {(["file", "paste"] as const).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); resetFile(); }}
            className={cn(
              "px-5 py-2 rounded-lg text-sm font-medium transition-all duration-200",
              tab === t
                ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                : "text-slate-400 hover:text-slate-200"
            )}
          >
            {t === "file" ? "📁 Fichier" : "📋 Coller"}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {tab === "file" ? (
          <motion.div
            key="file"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            {!selectedFile ? (
              <div
                {...getRootProps()}
                className={cn(
                  "relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300",
                  isDragActive
                    ? "border-indigo-500 bg-indigo-500/10 scale-[1.01]"
                    : "border-white/10 hover:border-indigo-500/50 hover:bg-white/[0.03]"
                )}
              >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center gap-4">
                  <div className={cn(
                    "w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300",
                    isDragActive ? "bg-indigo-500/30" : "bg-white/5"
                  )}>
                    <Upload className={cn(
                      "w-7 h-7 transition-colors",
                      isDragActive ? "text-indigo-400" : "text-slate-400"
                    )} />
                  </div>
                  <div>
                    <p className="text-slate-200 font-semibold text-lg mb-1">
                      {isDragActive ? "Déposez ici" : "Glissez-déposez votre fichier"}
                    </p>
                    <p className="text-slate-500 text-sm">
                      ou <span className="text-indigo-400 font-medium">parcourir</span>
                    </p>
                  </div>
                  <div className="flex gap-2 flex-wrap justify-center">
                    {[".xlsx", ".xls", ".csv", ".json"].map((ext) => (
                      <span key={ext} className="badge bg-white/5 border-white/10 text-slate-400">
                        {ext}
                      </span>
                    ))}
                  </div>
                  <p className="text-slate-600 text-xs">Max 50 MB · jusqu'à 100 000 lignes</p>
                </div>
              </div>
            ) : (
              <div className="glass-card p-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-6 h-6 text-indigo-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-200 truncate">{selectedFile.name}</p>
                    <p className="text-sm text-slate-500">
                      {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  {uploadState === "idle" && (
                    <button onClick={resetFile} className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-slate-200 transition-colors">
                      <X className="w-4 h-4" />
                    </button>
                  )}
                  {uploadState === "success" && <CheckCircle2 className="w-6 h-6 text-emerald-400" />}
                </div>

                {uploadState === "uploading" && (
                  <div className="mt-4">
                    <div className="flex justify-between text-xs text-slate-500 mb-2">
                      <span>Téléversement...</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        ) : (
          <motion.div
            key="paste"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <div className="glass-card p-4">
              <label className="block text-sm text-slate-400 mb-3 font-medium">
                Collez vos données (JSON, CSV, TSV, tableau copié-collé)
              </label>
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder={'[\n  {\n    "nom_fournisseur": "TotalEnergies",\n    "siret": "54205118800027"\n  }\n]\nou CSV / TSV...'}
                className="w-full h-48 bg-transparent border border-white/10 rounded-xl p-4 text-sm text-slate-300 font-mono placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/50 resize-none"
              />
              <p className="text-xs text-slate-600 mt-2">
                Formats acceptés : JSON (tableau d'objets), CSV, TSV (virgule, point-virgule, tabulation)
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 flex items-center gap-3 p-4 rounded-xl bg-red-500/10 border border-red-500/20"
        >
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-300">{error}</p>
        </motion.div>
      )}

      {/* CTA */}
      <div className="mt-6 flex items-center justify-between">
        <p className="text-xs text-slate-600">
          Les données restent sur votre serveur · Jamais partagées
        </p>
        <button
          onClick={handleUpload}
          disabled={
            uploadState === "uploading" ||
            uploadState === "success" ||
            (tab === "file" && !selectedFile) ||
            (tab === "paste" && !pasteText.trim())
          }
          className={cn(
            "btn-primary",
            (uploadState === "uploading" || uploadState === "success" ||
              (tab === "file" && !selectedFile) || (tab === "paste" && !pasteText.trim()))
              && "opacity-40 cursor-not-allowed transform-none shadow-none"
          )}
          id="upload-submit-btn"
        >
          {uploadState === "uploading" && <Loader2 className="w-4 h-4 animate-spin" />}
          {uploadState === "success" && <CheckCircle2 className="w-4 h-4" />}
          {uploadState === "idle" && <Upload className="w-4 h-4" />}
          {uploadState === "uploading" ? "Analyse en cours..." : uploadState === "success" ? "Redirigé..." : "Analyser les données"}
        </button>
      </div>
    </div>
  );
}
