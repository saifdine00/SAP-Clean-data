import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 120_000,
});

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UploadResponse {
  session_id: string;
  filename: string;
  total_rows: number;
  columns: string[];
  status: string;
  message?: string;
}

export interface Anomaly {
  id: string;
  session_id: string;
  row_index: number;
  column_name: string;
  anomaly_type: string;
  original_value: string | null;
  suggested_value: string | null;
  confidence: number;
  message: string;
  status: "pending" | "accepted" | "rejected" | "manual";
  corrected_value: string | null;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  filename: string;
  original_format: string;
  total_rows: number;
  status: "pending" | "analyzing" | "ready" | "exported";
  created_at: string;
  updated_at: string;
  column_mapping: Record<string, string>;
  summary: {
    total_anomalies: number;
    anomalies_by_type: Record<string, number>;
    total_rows: number;
    rows_with_issues: number;
  };
  anomalies: Anomaly[];
}

export interface SessionSummary {
  id: string;
  filename: string;
  total_rows: number;
  status: string;
  created_at: string;
  summary: SessionDetail["summary"];
}

export interface LLMSuggestion {
  source: "rules" | "llm";
  suggested_value: string | null;
  confidence: number;
  explanation: string;
  alternatives: string[];
}

// ── API calls ─────────────────────────────────────────────────────────────────

export const uploadFile = (file: File, onProgress?: (pct: number) => void) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post<UploadResponse>("/upload/file", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
};

export const uploadPaste = (text: string) => {
  const form = new FormData();
  form.append("text", text);
  return api.post<UploadResponse>("/upload/paste", form);
};

export const getSession = (id: string) =>
  api.get<SessionDetail>(`/analyze/session/${id}`);

export const getSessionStatus = (id: string) =>
  api.get<{ status: string; summary: SessionDetail["summary"] }>(`/analyze/session/${id}/status`);

export const listSessions = () =>
  api.get<SessionSummary[]>("/analyze/sessions");

export const applyCorrection = (
  anomalyId: string,
  action: "accept" | "reject" | "manual",
  manualValue?: string
) =>
  api.patch(`/corrections/${anomalyId}`, {
    anomaly_id: anomalyId,
    action,
    manual_value: manualValue,
  });

export const bulkAcceptHighConfidence = (sessionId: string, threshold = 0.8) =>
  api.post(`/corrections/bulk-accept-high-confidence?session_id=${sessionId}&threshold=${threshold}`);

export const getLLMSuggestion = (anomalyId: string) =>
  api.post<LLMSuggestion>(`/corrections/${anomalyId}/llm-suggest`);

export const exportCsv = (sessionId: string) =>
  `${API_URL}/api/v1/export/${sessionId}/csv`;

export const exportXlsx = (sessionId: string) =>
  `${API_URL}/api/v1/export/${sessionId}/xlsx`;

export const exportReportPdf = (sessionId: string) =>
  `${API_URL}/api/v1/export/${sessionId}/report/pdf`;

export const getReportJson = (sessionId: string) =>
  api.get(`/export/${sessionId}/report/json`);
