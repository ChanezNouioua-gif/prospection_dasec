const API_URL = "http://localhost:8000";

export async function getProspects(params?: { secteur?: string; score_min?: number }) {
  const query = new URLSearchParams(params as Record<string, string>).toString();
  const res = await fetch(`${API_URL}/prospects`, {
  credentials: "include",
   });
  if (!res.ok) throw new Error("Erreur chargement prospects");
  return res.json();
}

export async function getProspect(id: number) {
  const res = await fetch(`${API_URL}/prospects`, {
  credentials: "include",
   });
  if (!res.ok) throw new Error("Prospect introuvable");
  return res.json();
}