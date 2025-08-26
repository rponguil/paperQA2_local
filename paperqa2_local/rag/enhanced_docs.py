"""
Versión mejorada de la clase Docs de PaperQA2 que integra GROBID.

Mejoras sobre PaperQA2 original:
- Uso de HybridExtractor en lugar de PyPDF
- Metadata enriquecido de GROBID
- Mejor chunking basado en estructura de secciones
- Cache inteligente de documentos procesados
- Métricas de calidad de extracción
"""
import os
from dataclasses import dataclass
from typing import List, Dict, Any

import faiss
import numpy as np

from paperqa2_local.core.base import ExtractedDocument
from paperqa2_local.extractors.hybrid_extractor import HybridExtractor
from paperqa2_local.llm.local_llm import LocalLLMManager


@dataclass
class Chunk:
    """Represents a chunk of text from a document."""

    doc_key: str
    text: str
    section_title: str


@dataclass
class Document:
    """Represents a single processed document."""

    key: str
    metadata: Dict[str, Any]


@dataclass
class PQASession:
    """Holds the results of a single query session."""

    question: str
    answer: str
    contexts: List[Chunk]


class EnhancedDocs:
    """
    Enhanced version of PaperQA's Docs class, integrated with GROBID.
    """

    def __init__(
        self,
        extractor: HybridExtractor,
        llm_manager: LocalLLMManager,
        chunk_size: int = 2000,
        chunk_overlap: int = 300,
    ):
        self.extractor = extractor
        self.llm_manager = llm_manager
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # In-memory storage
        self.documents: Dict[str, Document] = {}
        self.chunks: List[Chunk] = []

        # FAISS index for vector search
        self.index = None
        self.embedding_dim: int = 0

    def _chunk_document(
        self, doc_key: str, extracted_doc: ExtractedDocument
    ) -> List[Chunk]:
        """Splits an extracted document into chunks based on sections."""
        new_chunks = []

        if extracted_doc.metadata.abstract:
            new_chunks.append(
                Chunk(
                    doc_key=doc_key,
                    text=extracted_doc.metadata.abstract,
                    section_title="Abstract",
                )
            )

        for section in extracted_doc.sections:
            # A more advanced implementation would split large sections.
            # For now, one section is one chunk.
            if section.text:
                new_chunks.append(
                    Chunk(
                        doc_key=doc_key, text=section.text, section_title=section.title
                    )
                )
        return new_chunks

    async def add_pdf(self, pdf_path: str, doc_key: str = None) -> Document:
        """
        Adds a PDF to the collection: extracts, chunks, embeds, and indexes.
        """
        if doc_key is None:
            doc_key = os.path.basename(pdf_path)

        if doc_key in self.documents:
            return self.documents[doc_key]

        # 1. Extract content
        extracted_doc = await self.extractor.extract_pdf(pdf_path)

        # 2. Chunk the document
        doc_chunks = self._chunk_document(doc_key, extracted_doc)
        if not doc_chunks:
            raise ValueError(f"No text could be chunked from document '{doc_key}'.")

        # 3. Generate embeddings for each chunk
        chunk_texts = [c.text for c in doc_chunks]
        embeddings = []
        # In a production system, this should be batched for efficiency.
        for text in chunk_texts:
            embedding = await self.llm_manager.embed_text(text)
            if embedding:
                embeddings.append(embedding)

        if not embeddings:
            raise ValueError(f"Could not generate embeddings for '{doc_key}'.")

        # 4. Add embeddings to the FAISS index
        embeddings_np = np.array(embeddings, dtype="float32")
        if self.index is None:
            self.embedding_dim = embeddings_np.shape[1]
            # Using IndexFlatL2, a basic index that stores the full vectors.
            self.index = faiss.IndexFlatL2(self.embedding_dim)

        self.index.add(embeddings_np)
        self.chunks.extend(doc_chunks)

        # 5. Store document metadata
        new_doc = Document(key=doc_key, metadata=extracted_doc.metadata.__dict__)
        self.documents[doc_key] = new_doc

        return new_doc

    async def query(self, question: str, k: int = 10) -> PQASession:
        """
        Query the indexed documents to answer a question.
        """
        if self.index is None:
            raise ValueError("Cannot query because no documents have been added.")

        # 1. Get embedding for the user's question
        query_embedding = await self.llm_manager.embed_text(question)
        query_np = np.array([query_embedding], dtype="float32")

        # 2. Search the FAISS index for the most relevant chunks
        distances, indices = self.index.search(query_np, k)

        # 3. Retrieve the actual chunk objects
        retrieved_chunks = []
        for i in indices[0]:
            # faiss returns -1 for indices if k > number of vectors
            if i != -1:
                retrieved_chunks.append(self.chunks[i])

        if not retrieved_chunks:
            return PQASession(
                question=question,
                answer="I could not find any relevant information in the documents.",
                contexts=[],
            )

        # 4. Construct a prompt with the retrieved contexts
        context_str = "\n\n---\n\n".join(
            [
                f"Source: {chunk.doc_key}, Section: {chunk.section_title}\n\n{chunk.text}"
                for chunk in retrieved_chunks
            ]
        )

        prompt = (
            "You are a helpful AI assistant. Please answer the user's question based "
            "on the context provided below. If the context does not contain the answer, "
            "say that you are unable to answer based on the provided information.\n\n"
            "Context:\n"
            f"{context_str}\n\n"
            "Question:\n"
            f"{question}\n\n"
            "Answer:"
        )

        # 5. Generate the final answer using the LLM
        answer = await self.llm_manager.generate_response(prompt)

        # 6. Return the complete session object
        return PQASession(
            question=question, answer=answer.strip(), contexts=retrieved_chunks
        )

    def save(self, directory: str = "paperqa_data"):
        """Saves the index and data to a directory."""
        if not os.path.exists(directory):
            os.makedirs(directory)

        if self.index is None:
            # Nothing to save
            return

        # Save the FAISS index
        faiss.write_index(self.index, os.path.join(directory, "docs.faiss"))

        # Save the rest of the data
        data_to_save = {
            "documents": self.documents,
            "chunks": self.chunks,
            "embedding_dim": self.embedding_dim,
        }
        with open(os.path.join(directory, "docs.pkl"), "wb") as f:
            import pickle

            pickle.dump(data_to_save, f)

    def load(self, directory: str = "paperqa_data"):
        """Loads the index and data from a directory."""
        index_path = os.path.join(directory, "docs.faiss")
        data_path = os.path.join(directory, "docs.pkl")

        if not os.path.exists(index_path) or not os.path.exists(data_path):
            return False

        # Load the FAISS index
        self.index = faiss.read_index(index_path)

        # Load the rest of the data
        with open(data_path, "rb") as f:
            import pickle

            data = pickle.load(f)
            self.documents = data["documents"]
            self.chunks = data["chunks"]
            self.embedding_dim = data["embedding_dim"]

        return True
