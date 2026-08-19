"""
Client LLM abstrait — les agents appellent `LLMClient.complete()`, jamais
directement le SDK Anthropic ou OpenAI. Changer de fournisseur = changer
LLM_PROVIDER dans config.py, aucun agent à modifier.
"""
from google import genai

import re
import time
from abc import ABC, abstractmethod

from config import LLM_PROVIDER, LLM_MODEL, ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEYS



class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str:
        ...



class GeminiLLMClient(LLMClient):
    def __init__(self):
        if not GEMINI_API_KEYS:
            raise RuntimeError("Aucune clé Gemini configurée (GEMINI_API_KEYS manquante dans le .env).")

        self._clients = [genai.Client(api_key=k) for k in GEMINI_API_KEYS]
        # index de la clé courante
        self._idx = 0
        # timestamp (time.time()) avant lequel chaque clé est en pause (0 = disponible tout de suite)
        self._pause_jusqu_a = [0.0] * len(self._clients)

    def _extraire_retry_delay(self, erreur) -> float:
        """Essaie de lire le retryDelay renvoyé par Gemini dans le message d'erreur, sinon 60s par défaut."""
        m = re.search(r"retryDelay['\"]?\s*:\s*['\"](\d+)s", str(erreur))
        if m:
            return float(m.group(1))
        return 60.0

    def _prochaine_cle_disponible(self):
        """Retourne l'indice de la première clé disponible, en attendant si besoin qu'une se libère."""
        maintenant = time.time()
        indices_dispo = [i for i in range(len(self._clients)) if self._pause_jusqu_a[i] <= maintenant]
        if indices_dispo:
            # on tourne en round-robin parmi celles dispo, en partant de l'index courant
            for offset in range(len(self._clients)):
                i = (self._idx + offset) % len(self._clients)
                if i in indices_dispo:
                    return i
        # aucune clé dispo -> on attend la plus proche à se libérer
        i_min = min(range(len(self._clients)), key=lambda i: self._pause_jusqu_a[i])
        attente = max(0.0, self._pause_jusqu_a[i_min] - maintenant)
        if attente > 0:
            print(f"[GEMINI] toutes les clés sont en quota dépassé, attente {attente:.0f}s avant de réessayer (clé {i_min})")
            time.sleep(attente)
        return i_min

    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str:
        max_tokens_effectif = max(max_tokens, 2000)
        derniere_erreur = None

        # on essaie chaque clé au plus une fois par appel à complete()
        for _ in range(len(self._clients)):
            i = self._prochaine_cle_disponible()
            self._idx = i
            client = self._clients[i]
            try:
                response = client.models.generate_content(
                    model=LLM_MODEL,
                    contents=f"{system}\n\n{prompt}",
                    config={
                        "temperature": 0,
                        "max_output_tokens": max_tokens_effectif,
                    },
                )

                candidat = response.candidates[0] if response.candidates else None
                finish_reason = getattr(candidat, "finish_reason", None) if candidat else None

                texte = response.text
                if not texte:
                    raise RuntimeError(
                        f"Gemini n'a renvoyé aucun texte exploitable (finish_reason={finish_reason})"
                    )
                if finish_reason and str(finish_reason) not in ("STOP", "1", "FinishReason.STOP"):
                    print(f"[GEMINI] réponse potentiellement tronquée, finish_reason={finish_reason}")

                self._idx = (i + 1) % len(self._clients)  # prochaine fois, on essaie la suivante en priorité
                return texte.strip()

            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    delai = self._extraire_retry_delay(e)
                    self._pause_jusqu_a[i] = time.time() + delai
                    print(f"[GEMINI] clé #{i} en quota dépassé, mise en pause {delai:.0f}s, tentative avec la clé suivante")
                    derniere_erreur = e
                    continue
                raise  # autre type d'erreur -> on ne masque pas, on la laisse remonter

        raise RuntimeError(f"Toutes les clés Gemini ont échoué (dernière erreur : {derniere_erreur})")

class AnthropicLLMClient(LLMClient):
    def __init__(self):
        import anthropic
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY manquante dans l'environnement (.env).")
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str:
        reponse = self.client.messages.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(bloc.text for bloc in reponse.content if bloc.type == "text")


class OpenAILLMClient(LLMClient):
    def __init__(self):
        from openai import OpenAI
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY manquante dans l'environnement (.env).")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def complete(self, system: str, prompt: str, max_tokens: int = 300) -> str:
        reponse = self.client.chat.completions.create(
            model=LLM_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return reponse.choices[0].message.content


def get_llm_client():
    print("Provider =", repr(LLM_PROVIDER))

    if LLM_PROVIDER == "gemini":
        return GeminiLLMClient()

    elif LLM_PROVIDER == "anthropic":
        return AnthropicLLMClient()

    elif LLM_PROVIDER == "openai":
        return OpenAILLMClient()

    raise ValueError(f"LLM_PROVIDER inconnu : {repr(LLM_PROVIDER)}")
