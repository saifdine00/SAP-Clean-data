import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const ANOMALY_TYPE_LABELS: Record<string, string> = {
  duplicate_exact: "Doublon exact",
  duplicate_near: "Doublon approché",
  duplicate_siret: "SIRET dupliqué",
  invalid_siret: "SIRET invalide",
  invalid_siren: "SIREN invalide",
  invalid_iban: "IBAN invalide",
  invalid_email: "Email invalide",
  invalid_phone: "Téléphone invalide",
  invalid_date: "Date invalide",
  invalid_amount: "Montant invalide",
  missing_required: "Champ requis manquant",
  invalid_payment_terms: "Conditions de paiement SAP invalides",
  invalid_account_group: "Groupe de compte SAP invalide",
  field_too_long: "Champ trop long",
  special_characters: "Caractères spéciaux SAP",
  mixed_currency: "Devises mixtes",
};

export const ANOMALY_TYPE_COLORS: Record<string, string> = {
  duplicate_exact: "bg-red-500/20 text-red-300 border-red-500/30",
  duplicate_near: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  duplicate_siret: "bg-red-500/20 text-red-300 border-red-500/30",
  invalid_siret: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  invalid_siren: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  invalid_iban: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  invalid_email: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  invalid_phone: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  invalid_date: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  invalid_amount: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  missing_required: "bg-red-600/20 text-red-400 border-red-600/30",
  invalid_payment_terms: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  invalid_account_group: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
  field_too_long: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  special_characters: "bg-pink-500/20 text-pink-300 border-pink-500/30",
  mixed_currency: "bg-teal-500/20 text-teal-300 border-teal-500/30",
};

export const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return "text-emerald-400";
  if (confidence >= 0.5) return "text-yellow-400";
  return "text-red-400";
};

export const getConfidenceLabel = (confidence: number) => {
  if (confidence >= 0.8) return "Élevée";
  if (confidence >= 0.5) return "Moyenne";
  return "Faible";
};

export const formatDate = (iso: string) => {
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};
