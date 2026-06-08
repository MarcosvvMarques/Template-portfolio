"""Function-calling / tool-use — registro de tools usadas pelo agente.

Reaproveita o LAB-001. Voce vai preencher 1 TODO aqui (sua tool especifica).
"""

from __future__ import annotations

import json
from typing import Any, Callable


"""Function-calling / tool-use — registro de tools usadas pelo agente."""


# ============================================================================
# TODO 4 — Sua tool especifica do dominio (Pro Git)
# ============================================================================

def lookup_chapter(chapter: int) -> str:
    """Retorna o sumário e tópicos principais do capítulo N do livro Pro Git."""
    chapters = {
        1: "Capítulo 1: Getting Started. Cobre controle de versão, história do Git, instalação e configuração inicial.",
        2: "Capítulo 2: Git Basics. Cobre como obter um repositório, gravar mudanças (add, commit), ver o histórico (log), desfazer coisas e trabalhar com remotos (push, pull).",
        3: "Capítulo 3: Git Branching. Cobre criação de branches, merge, gerenciamento, workflows, remote branches e rebasing.",
        4: "Capítulo 4: Git on the Server. Cobre protocolos de rede, configuração de servidor, chaves SSH públicas, GitWeb e GitLab.",
        5: "Capítulo 5: Distributed Git. Cobre workflows distribuídos, contribuição e manutenção de projetos.",
        6: "Capítulo 6: GitHub. Cobre configuração de conta, contribuição em projetos, manutenção e ferramentas do GitHub.",
        7: "Capítulo 7: Git Tools. Cobre seleção de revisões, stashing, busca (grep), reescrita de histórico (rebase interativo), reset e debugging (bisect).",
        8: "Capítulo 8: Customizing Git. Cobre configuração avançada, atributos e Git Hooks.",
        9: "Capítulo 9: Git and Other Systems. Cobre uso do Git como cliente e migração para o Git.",
        10: "Capítulo 10: Git Internals. Cobre encanamento (plumbing), objetos do Git (trees, commits), referências, packfiles e refspecs."
    }

    if chapter in chapters:
        return chapters[chapter]
    return f"Capítulo {chapter} não encontrado. O livro Pro Git possui apenas capítulos de 1 a 10."


# Schema JSON que o LLM lê para saber como usar a função
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "lookup_chapter",
            "description": "Retorna os tópicos principais de um capítulo específico do livro Pro Git. Útil para saber em qual capítulo focar a busca.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chapter": {
                        "type": "integer",
                        "description": "O número do capítulo para consultar (ex: 1, 2, 3... até 10)."
                    }
                },
                "required": ["chapter"]
            }
        }
    }
]

# Registro da função para execução dinâmica
TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "lookup_chapter": lookup_chapter,
}


def run_tool_call(name: str, arguments_json: str) -> str:
    """Executa uma tool call e retorna o resultado como string."""
    if name not in TOOL_REGISTRY:
        return f"ERROR: tool '{name}' nao registrada"
    try:
        kwargs = json.loads(arguments_json)
        return TOOL_REGISTRY[name](**kwargs)
    except Exception as e:
        return f"ERROR ao executar {name}: {e}"
