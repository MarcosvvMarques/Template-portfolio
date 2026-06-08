"""Model routing cheap-first com fallback.

Reaproveita o notebook 05. Voce vai preencher 1 TODO aqui.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass(frozen=True)
class RouteDecision:
    model: str
    complexity: str  # "simple" | "complex"
    reason: str


# ------------------------------------------------------------------ TODO 6
def classify_complexity(query: str) -> RouteDecision:
    """Classifica complexidade da query para escolher modelo (cheap vs premium)."""

    # Lendo do .env ou usando defaults
    cheap_model = os.environ.get("LLM_MODEL", "gemini-2.5-flash-lite")
    premium_model = os.environ.get("PREMIUM_MODEL", "gemini-1.5-pro")

    query_lower = query.lower()

    # 1. Lista de palavras que exigem síntese ou raciocínio profundo
    complex_keywords = [
        "explique", "compare", "diferença", "resuma", "analise",
        "por que", "como funciona", "passo a passo", "detalhes"
    ]

    # Regra A: Contém palavras de raciocínio
    if any(word in query_lower for word in complex_keywords):
        return RouteDecision(
            model=premium_model,
            complexity="complex",
            reason="Detectada palavra-chave analítica (ex: explique, compare, por que)."
        )

    # Regra B: Pergunta muito longa (geralmente significa contexto complexo)
    if len(query) > 100:
        return RouteDecision(
            model=premium_model,
            complexity="complex",
            reason="Query longa (> 100 caracteres), roteando para modelo com maior atenção."
        )

    # Regra C: Fallback para o modelo barato
    return RouteDecision(
        model=cheap_model,
        complexity="simple",
        reason="Query curta e direta. Roteada para modelo rápido e barato."
    )


def make_client() -> OpenAI:
    """Cliente OpenAI-compatible para o provider configurado."""
    if "GEMINI_API_KEY" in os.environ:
        return OpenAI(
            api_key=os.environ["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    return OpenAI()
