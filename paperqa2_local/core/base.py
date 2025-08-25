from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Author:
    """Represents a single author."""
    name: str

@dataclass
class DocumentSection:
    """Represents a section of a document."""
    title: str
    text: str

@dataclass
class Reference:
    """Represents a bibliographic reference."""
    text: str

@dataclass
class Figure:
    """Represents a figure or table in the document."""
    caption: str

@dataclass
class DocumentMetadata:
    """Structured metadata extracted by GROBID."""
    title: Optional[str] = None
    authors: List[Author] = field(default_factory=list)
    abstract: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    doi: Optional[str] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    language: Optional[str] = None
    document_type: Optional[str] = None

@dataclass
class ExtractedDocument:
    """A document extracted with enriched metadata."""
    text: str
    metadata: DocumentMetadata
    sections: List[DocumentSection] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    figures: List[Figure] = field(default_factory=list)
    quality_score: float = 0.0
    extraction_method: str = "unknown"
    processing_time: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)
