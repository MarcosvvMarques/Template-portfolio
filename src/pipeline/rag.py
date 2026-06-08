"""RAG pipeline — chunk, embed, index, retrieve, generate.

Reaproveita as funcoes do notebook 02. Voce vai preencher 3 TODOs aqui.
"""

from __future__ import annotations

import os
import uuid
import time
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from typing import Any

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from openai import OpenAI


def _make_client() -> tuple[OpenAI, str | None]:
    """Inicializa cliente OpenAI-compatible conforme provider escolhido no .env."""
    if "GEMINI_API_KEY" in os.environ:
        client = OpenAI(
            api_key=os.environ["GEMINI_API_KEY"],
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        embed_api_base = "https://generativelanguage.googleapis.com/v1beta/openai/"
    elif "OPENAI_API_KEY" in os.environ:
        client = OpenAI()
        embed_api_base = None
    else:
        raise RuntimeError(
            "Configure GEMINI_API_KEY ou OPENAI_API_KEY no .env")
    return client, embed_api_base


class RAGPipeline:
    """Pipeline RAG end-to-end com Chroma local."""

    def __init__(
        self,
        corpus_dir: str = "data/corpus",
        persist_dir: str = "data/chroma",
        collection_name: str = "docs",
        llm_model: str | None = None,
        embed_model: str | None = None,
    ) -> None:
        self.client, embed_api_base = _make_client()
        self.llm_model = llm_model or os.environ.get(
            "LLM_MODEL", "gemini-2.5-flash-lite")
        self.embed_model = embed_model or os.environ.get(
            "EMBED_MODEL", "gemini-embedding-001")

        embed_kwargs: dict[str, Any] = {
            "api_key": os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            "model_name": self.embed_model,
        }
        if embed_api_base:
            embed_kwargs["api_base"] = embed_api_base
        self.embed_fn = OpenAIEmbeddingFunction(**embed_kwargs)

        self.corpus_dir = Path(corpus_dir)
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        chroma = chromadb.PersistentClient(path=persist_dir)
        self.collection = chroma.get_or_create_collection(
            name=collection_name, embedding_function=self.embed_fn  # type: ignore
        )

    # ------------------------------------------------------------------ TODO 1
    def ingest_and_index(self) -> int:
        """Le PDFs de `corpus_dir`, faz chunking e indexa em Chroma."""

        docs: list[dict] = []
        for pdf_path in self.corpus_dir.glob("*.pdf"):
            reader = PdfReader(pdf_path)

            # Lendo apenas 12 páginas de conteúdo real (pulando as 10 primeiras do sumário)
            for i, page in enumerate(reader.pages[10:22]):
                text = page.extract_text()
                if text:
                    docs.append({
                        "text": text,
                        "source": pdf_path.name,
                        "page": i + 10
                    })

        # SEU CODIGO AQUI — TODO 1.B
        chunks: list[dict] = []
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100
        )

        for doc in docs:
            doc_chunks = splitter.split_text(doc["text"])
            for chunk_text in doc_chunks:
                chunks.append({
                    "id": str(uuid.uuid4()),
                    "text": chunk_text,
                    "source": doc["source"],
                    "page": doc["page"]
                })

        # SEU CODIGO AQUI — TODO 1.C
        if chunks:
            batch_size = 90  # Limite de batch
            print(
                f"\nIniciando indexação de {len(chunks)} chunks no ChromaDB..")

            for i in range(0, len(chunks), batch_size):
                lote = chunks[i: i + batch_size]
                self.collection.add(
                    ids=[c["id"] for c in lote],
                    documents=[c["text"] for c in lote],
                    metadatas=[{"source": c["source"], "page": c["page"]}
                               for c in lote]
                )
                print(f"Indexados {i + len(lote)}/{len(chunks)}...")

                if i + batch_size < len(chunks):
                    print("Aguardando 60s para evitar Rate Limit da API...")
                    time.sleep(60)

        return self.collection.count()

    # ------------------------------------------------------------------ TODO 2
    def retrieve(self, query: str, k: int = 5) -> list[dict]:
        """Busca top-k chunks similares a query."""
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )

        hits: list[dict] = []

        docs_result = results.get("documents")
        meta_result = results.get("metadatas")
        dist_result = results.get("distances")

        if docs_result and meta_result and docs_result[0]:
            docs = docs_result[0]
            metadatas = meta_result[0]
            distances = dist_result[0] if dist_result else [0.0] * len(docs)

            for i in range(len(docs)):
                hits.append({
                    "text": docs[i],
                    "source": metadatas[i]["source"],
                    "page": metadatas[i]["page"],
                    "distance": distances[i]
                })
        return hits

    # ------------------------------------------------------------------ TODO 3
    def answer(self, question: str, k: int = 5) -> dict:
        """Pipeline completo: retrieve + augment + generate. Retorna {answer, sources}."""
        hits = self.retrieve(question, k=k)

        # 1. Monta contexto
        context_parts = []
        for hit in hits:
            context_parts.append(
                f"[{hit['source']}:{hit['page']}]\n{hit['text']}")
        context_str = "\n\n".join(context_parts)

        # 2. Constrói prompt
        prompt = PROMPT_TEMPLATE.format(context=context_str, question=question)

        # 3. Chamar LLM (usando a interface OpenAI-compatible)
        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=[{"role": "user", "content": prompt}]
        )
        answer_text = response.choices[0].message.content

        # 4. Formata e retorna resultado
        sources = [(h["source"], h["page"]) for h in hits]
        # Remover duplicatas mantendo a ordem para a lista de fontes
        unique_sources = []
        for s in sources:
            if s not in unique_sources:
                unique_sources.append(s)

        return {
            "answer": answer_text,
            "sources": unique_sources
        }


PROMPT_TEMPLATE = """Voce e um assistente tecnico. Responda APENAS com base no contexto abaixo.
Se a informacao nao estiver no contexto, diga "Nao encontrado no corpus".
Sempre cite a fonte usando o formato [arquivo:pagina].

CONTEXTO:
{context}

PERGUNTA: {question}

RESPOSTA:"""


def build_rag_pipeline(corpus_dir: str = "data/corpus") -> RAGPipeline:
    """Factory: cria pipeline e indexa corpus se ainda nao indexado."""
    pipeline = RAGPipeline(corpus_dir=corpus_dir)
    if pipeline.collection.count() == 0:
        pipeline.ingest_and_index()
    return pipeline
