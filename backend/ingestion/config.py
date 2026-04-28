"""Source configurations for the ingestion pipeline."""

from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    source_id: str
    display_name: str
    source_type: str  # "html_docs" | "api_ref" | "cli_ref" | "json_kb"
    urls: list[str]
    language: str = "en"
    # For json_kb sources, local file paths (in addition to / instead of urls)
    file_paths: list[str] = field(default_factory=list)


# Knowledge base JSON files from teo-psa-aiagents repo
_KB_BASE = (
    "/Users/wesleysum/Projects/teo-psa-aiagents/"
    "accelerationConversionAgent/knowledge-base"
)

SOURCE_CONFIGS: list[SourceConfig] = [
    SourceConfig(
        source_id="edgeone-docs",
        display_name="EdgeOne Public Docs",
        source_type="html_docs",
        urls=["https://cloud.tencent.com/document/product/1552"],
        language="en",
    ),
    SourceConfig(
        source_id="cli-reference",
        display_name="tccli CLI Reference",
        source_type="cli_ref",
        urls=["https://cloud.tencent.com/document/product/1552"],
        language="en",
    ),
    SourceConfig(
        source_id="api-reference",
        display_name="EdgeOne API Reference",
        source_type="api_ref",
        urls=["https://cloud.tencent.com/document/product/1552"],
        language="en",
    ),
    SourceConfig(
        source_id="error-patterns",
        display_name="TEO-PSA Knowledge Base",
        source_type="json_kb",
        urls=[],
        language="en",
        file_paths=[
            f"{_KB_BASE}/mappings.json",
            f"{_KB_BASE}/error-patterns.json",
            f"{_KB_BASE}/edge-functions.json",
            f"{_KB_BASE}/ignore-list.json",
            f"{_KB_BASE}/source-index.json",
        ],
    ),
]

# Lookup map for convenience
SOURCE_CONFIG_MAP: dict[str, SourceConfig] = {
    cfg.source_id: cfg for cfg in SOURCE_CONFIGS
}
