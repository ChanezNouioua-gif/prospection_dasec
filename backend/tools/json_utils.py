"""Utilitaire partagé pour nettoyer les réponses JSON d'un LLM (retire les
balises markdown ```json ... ``` que certains modèles ajoutent malgré la consigne)."""

import re


def nettoyer_json(texte: str) -> str:
    texte = texte.strip()
    if texte.startswith("```"):
        texte = texte.split("```")[1]
        texte = texte.removeprefix("json").strip()
    return texte


def extraire_champ_regex(texte: str, cle: str) -> str | None:
    """Filet de sécurité si le JSON est tronqué (réponse coupée par max_tokens) :
    tente d'extraire la valeur d'une clé même dans un JSON invalide/incomplet.
    Ne remplace pas un vrai parsing JSON — utilisé seulement en dernier recours."""
    correspondance = re.search(rf'"{cle}"\s*:\s*"([^"]*)', texte)
    return correspondance.group(1) if correspondance else None