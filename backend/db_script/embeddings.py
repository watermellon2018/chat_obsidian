import os
from pathlib import Path

import re
from dotenv import load_dotenv
from langchain_text_splitters import MarkdownTextSplitter
from langchain_core.documents import Document

load_dotenv()



# Ignore images in markdown
def clean_markdown_images(text: str) -> str:
    # 1. Remove ![alt](path)
    # 2. Remove ![[image.png]]
    pattern = r'!\[\[.*?\]\]|!\[.*?\]\(.*?\)'
    return re.sub(pattern, '', text)


# Read data from vault
def build_chunks(vault_path: Path) -> list[Document]:
    """Read data from vault"""
    documents: list[Document] = []
    for file_path in vault_path.rglob("*.md"):
        if ".obsidian" in file_path.parts:
            continue
        
        note_title = file_path.stem

        # Avoid limit of the length of the path in Windows
        file_path = str(file_path.absolute())
        if os.name == 'nt' and not file_path.startswith('\\\\?\\'):
            file_path = '\\\\?\\' + file_path

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = f.read()

        data = clean_markdown_images(raw_data)
        for chunk in split_text(data):
            content_with_context = f"Note: {note_title}\nContent: {chunk}"
            documents.append(
                Document(
                    page_content=content_with_context,
                    metadata={"source": note_title, "path": str(file_path)},
                )
            )

    return documents


def split_text(text: str, chunk_size: int = 4000, chunk_overlap: int = 100) -> list[str]:
    splitter = MarkdownTextSplitter(
        chunk_overlap=chunk_overlap,
        chunk_size=chunk_size,
    )
    chunks = splitter.split_text(text)
    return chunks