"""
Extractor principal que usa GROBID para procesamiento de PDFs científicos.
"""
import asyncio
import functools
import re
import time
from typing import Dict, Any, List

from grobid_client.grobid_client import GrobidClient
from lxml import etree

from paperqa2_local.core.base import (
    ExtractedDocument,
    DocumentMetadata,
    Author,
    DocumentSection,
    Reference,
    Figure,
)


class GrobidExtractor:
    """
    Extractor that uses GROBID for processing scientific PDFs.
    """

    def __init__(self, grobid_server_url: str = "http://localhost:8070"):
        """Inicializar extractor GROBID con configuración personalizable."""
        self.grobid_server_url = grobid_server_url
        self.client = GrobidClient(grobid_server_url, check_server=True)
        self.ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    async def extract_pdf(self, pdf_path: str) -> ExtractedDocument:
        """
        Procesar PDF usando GROBID y retornar documento estructurado.
        """
        start_time = time.time()
        loop = asyncio.get_running_loop()

        process_func = functools.partial(
            self.client.process,
            "processFulltextDocument",
            pdf_path,
            generateIDs=True,
            consolidate_header=True,
            consolidate_citations=True,
        )
        try:
            _, _, tei_xml_bytes = await loop.run_in_executor(None, process_func)
        except Exception as e:
            raise IOError(f"Failed to process PDF with GROBID: {e}") from e

        if not tei_xml_bytes:
            raise ValueError("GROBID processing failed, returned empty response.")

        tei_xml_string = tei_xml_bytes.decode("utf-8")
        parsed_data = self._parse_tei_xml(tei_xml_string)
        processing_time = time.time() - start_time

        extracted_doc = ExtractedDocument(
            text=parsed_data["text"],
            metadata=parsed_data["metadata"],
            sections=parsed_data["sections"],
            references=parsed_data["references"],
            figures=parsed_data["figures"],
            extraction_method="grobid",
            processing_time=processing_time,
            raw_data={"tei_xml": tei_xml_string},
        )

        extracted_doc.quality_score = self.validate_extraction(extracted_doc)
        return extracted_doc

    def _parse_tei_xml(self, tei_xml_string: str) -> Dict[str, Any]:
        """Parse the TEI XML string to extract structured data."""
        parser = etree.XMLParser(remove_blank_text=True, recover=True)
        root = etree.fromstring(tei_xml_string.encode("utf-8"), parser)

        metadata = self._extract_metadata(root)
        sections = self._extract_sections(root)
        references = self._extract_references(root)
        figures = self._extract_figures(root)
        text_content = self.tei_to_markdown(root)

        return {
            "metadata": metadata,
            "sections": sections,
            "references": references,
            "figures": figures,
            "text": text_content,
        }

    def _extract_metadata(self, root) -> DocumentMetadata:
        """Extract metadata from the TEI XML root."""
        title = root.xpath(".//tei:titleStmt/tei:title/text()", namespaces=self.ns)
        abstract_nodes = root.xpath(".//tei:profileDesc/tei:abstract//text()", namespaces=self.ns)
        abstract = " ".join(abstract_nodes).strip()
        keywords = root.xpath(".//tei:profileDesc/tei:textClass/tei:keywords/tei:term/text()", namespaces=self.ns)

        authors = []
        # Restrict author search to the main document's file description
        author_elements = root.xpath(
            "/tei:TEI/tei:teiHeader/tei:fileDesc//tei:analytic/tei:author",
            namespaces=self.ns,
        )
        for author_el in author_elements:
            pers_name = author_el.find("tei:persName", self.ns)
            if pers_name is not None:
                firstname_el = pers_name.find("tei:forename", self.ns)
                surname_el = pers_name.find("tei:surname", self.ns)
                firstname = firstname_el.text if firstname_el is not None else ""
                surname = surname_el.text if surname_el is not None else ""
                authors.append(Author(name=f"{firstname} {surname}".strip()))

        doi = root.xpath(".//tei:idno[@type='DOI']/text()", namespaces=self.ns)
        journal = root.xpath(".//tei:monogr/tei:title/text()", namespaces=self.ns)
        year_el = root.xpath(".//tei:publicationStmt/tei:date[@type='published']/@when", namespaces=self.ns)

        return DocumentMetadata(
            title=title[0] if title else None,
            abstract=abstract if abstract else None,
            authors=authors,
            keywords=keywords,
            doi=doi[0] if doi else None,
            journal=journal[0] if journal else None,
            year=int(year_el[0].split("-")[0]) if year_el else None,
        )

    def _extract_sections(self, root) -> List[DocumentSection]:
        """Extract sections from the TEI XML root."""
        sections = []
        for div in root.xpath(".//tei:body/tei:div", namespaces=self.ns):
            head_el = div.find("tei:head", self.ns)
            if head_el is not None and head_el.text:
                title = head_el.text.strip()
                # Join text from all paragraphs within the section
                paragraphs = div.xpath(".//tei:p//text()", namespaces=self.ns)
                section_text = "\n".join(p.strip() for p in paragraphs if p.strip())
                if section_text:
                    sections.append(DocumentSection(title=title, text=section_text))
        return sections

    def _extract_references(self, root) -> List[Reference]:
        """Extract references from the TEI XML root."""
        references = []
        for ref_el in root.xpath(".//tei:listBibl/tei:biblStruct", namespaces=self.ns):
            ref_text = "".join(ref_el.xpath(".//text()"))
            if ref_text:
                references.append(Reference(text=ref_text.strip()))
        return references

    def _extract_figures(self, root) -> List[Figure]:
        """Extract figures and tables from the TEI XML root."""
        figures = []
        for fig_el in root.xpath(".//tei:figure", namespaces=self.ns):
            caption_text = "".join(fig_el.xpath(".//tei:head//text() | .//tei:figDesc//text()", namespaces=self.ns))
            if caption_text:
                figures.append(Figure(caption=caption_text.strip()))
        return figures

    def tei_to_markdown(self, root) -> str:
        """Convert TEI XML body to structured markdown."""
        body = root.find(".//tei:body", self.ns)
        if body is None:
            return ""

        def _node_to_markdown(node):
            if node is None:
                return ""

            parts = [node.text or ""]
            for child in node:
                tag = etree.QName(child.tag).localname

                if tag == "head":
                    level = len(child.get("n", "1").split(".")) + 1
                    parts.append(f"\n\n{'#' * level} {''.join(child.itertext()).strip()}\n\n")
                elif tag == "p":
                    parts.append(f"{''.join(child.itertext()).strip()}\n\n")
                elif tag == "ref":
                    # For now, just render the text of a reference
                    pass # Often noisy, skip inline
                else:
                    # Generic recursion for other tags
                    parts.append(_node_to_markdown(child))

                if child.tail:
                    parts.append(child.tail)

            return "".join(parts)

        # Process abstract as the first part
        abstract = self._extract_metadata(root).abstract
        md_parts = [f"## Abstract\n\n{abstract}\n\n" if abstract else ""]

        # Process body
        for div in body.xpath("./tei:div", namespaces=self.ns):
            md_parts.append(_node_to_markdown(div))

        full_text = "".join(md_parts)
        # Clean up excessive newlines and whitespace
        full_text = re.sub(r"\n{3,}", "\n\n", full_text)
        full_text = re.sub(r" +", " ", full_text)
        return full_text.strip()

    def validate_extraction(self, extracted_doc: ExtractedDocument) -> float:
        """Validar calidad de extracción y retornar score 0-1."""
        score = 0.0
        if extracted_doc.metadata.title and len(extracted_doc.metadata.title) > 5:
            score += 0.3
        if extracted_doc.metadata.abstract and len(extracted_doc.metadata.abstract) > 20:
            score += 0.3
        if extracted_doc.sections and len(extracted_doc.sections) > 0:
            score += 0.2
        if extracted_doc.references and len(extracted_doc.references) > 0:
            score += 0.1
        if len(extracted_doc.text) > 500:
            score += 0.1

        return min(round(score, 2), 1.0)
