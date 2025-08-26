"""
CLI compatible con PaperQA2 original pero con funcionalidades extendidas.

Comandos requeridos:
- ask: hacer preguntas (compatible con pqa ask)
- add: añadir documentos
- index: crear/administrar índices
- config: configurar sistema
- status: estado del sistema y modelos
- extract: modo de solo extracción para testing
- benchmark: comparar calidad de extracción
"""
import asyncio
import click
import os
from rich.console import Console
from rich.markdown import Markdown

from paperqa2_local.extractors import (
    GrobidExtractor,
    FallbackExtractor,
    HybridExtractor,
)
from paperqa2_local.llm import LocalLLMManager, LocalLLMConfig
from paperqa2_local.rag import EnhancedDocs

# Default path for storing the index data
INDEX_DIR = os.path.expanduser("~/.paperqa2-local/index")


def initialize_components():
    """Helper function to instantiate and return all core components."""
    # For now, we use default configs. Later, this could read from a YAML file.
    grobid_extractor = GrobidExtractor()
    fallback_extractor = FallbackExtractor()
    hybrid_extractor = HybridExtractor(
        grobid_extractor=grobid_extractor, fallback_extractor=fallback_extractor
    )
    llm_config = LocalLLMConfig()
    llm_manager = LocalLLMManager(llm_config)
    docs = EnhancedDocs(extractor=hybrid_extractor, llm_manager=llm_manager)
    return docs


@click.group()
def cli():
    """PaperQA2 Local - A RAG system with GROBID and local LLMs."""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
def add(pdf_path):
    """Adds a new PDF document to the index."""
    console = Console()
    console.print(f"Initializing system to add '[bold cyan]{pdf_path}[/bold cyan]'...")

    docs = initialize_components()
    docs.load(INDEX_DIR)

    async def _add_and_save():
        try:
            with console.status("[bold green]Processing document...", spinner="dots"):
                await docs.add_pdf(pdf_path)
            console.print(
                f"✅ [bold green]Successfully added '{pdf_path}' to the index.[/bold green]"
            )
            docs.save(INDEX_DIR)
            console.print(f"💾 Index saved to '{INDEX_DIR}'")
        except Exception as e:
            console.print(f"❌ [bold red]Error adding document: {e}[/bold red]")
        finally:
            await docs.llm_manager.close()

    asyncio.run(_add_and_save())


@cli.command()
@click.argument("question")
@click.option(
    "-k", "--k-contexts", default=5, help="Number of context chunks to retrieve."
)
def ask(question, k_contexts):
    """Asks a question about the indexed documents."""
    console = Console()

    if not os.path.exists(INDEX_DIR):
        console.print(
            "❌ [bold red]No index found. Please add a document first using the 'add' command.[/bold red]"
        )
        return

    console.print("Initializing system and loading index...")
    docs = initialize_components()
    docs.load(INDEX_DIR)

    async def _query_and_print():
        try:
            with console.status("[bold green]Searching for answer...", spinner="dots"):
                session = await docs.query(question, k=k_contexts)

            console.print("\n[bold green]Answer:[/bold green]")
            console.print(session.answer)

            console.print("\n[bold yellow]Sources:[/bold yellow]")
            if session.contexts:
                for i, context in enumerate(session.contexts, 1):
                    source_md = f"""
**{i}. Source:** `{context.doc_key}`
**Section:** `{context.section_title}`
> {context.text[:300].strip()}...
"""
                    console.print(Markdown(source_md))
            else:
                console.print("No sources were used to generate this answer.")

        except Exception as e:
            console.print(f"❌ [bold red]Error during query: {e}[/bold red]")
        finally:
            await docs.llm_manager.close()

    asyncio.run(_query_and_print())


if __name__ == "__main__":
    cli()
