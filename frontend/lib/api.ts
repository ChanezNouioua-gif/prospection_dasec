export const API_URL = "http://localhost:8000";
export async function logout() {
  const res = await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) throw new Error("Erreur lors de la déconnexion");
  return res.json();
}

export async function getCurrentUser() {
  const res = await fetch(`${API_URL}/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Non authentifié");
  return res.json();
}

export async function getResumeCrm() {
  const res = await fetch(`${API_URL}/crm/resume`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Erreur chargement du résumé CRM");
  return res.json();
}