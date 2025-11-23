import os
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

PDF_DIR = './pdf-files'
CHUNK_SIZE = 2048  # 2 KB
PERSIST_DIR = './vector-data'  # Directory for persistent storage

# Ensure the persist directory exists
os.makedirs(PERSIST_DIR, exist_ok=True)

# Initialize embedding model
model = SentenceTransformer('intfloat/multilingual-e5-base')

# Initialize ChromaDB with persistent storage
tmp_settings = Settings(anonymized_telemetry=False, persist_directory="./vector-data")
#client = chromadb.Client(tmp_settings)
client = chromadb.PersistentClient(path=PERSIST_DIR)
collection = client.get_or_create_collection('pdf_chunks')


def read_pdfs_from_dir(directory):
    """
    Yields full file paths of PDF files in the provided directory.

    Args:
        directory (str): Directory path to search for PDF files.

    Yields:
        str: Full path to a PDF file found in the directory.
    """
    pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
    for pdf_file in pdf_files:
        yield os.path.join(directory, pdf_file)

def extract_text_from_pdf(pdf_path):
    """
    Extracts text content from all pages of a PDF file.

    Args:
        pdf_path (str): Path to the PDF file.

    Returns:
        str: Combined extracted text from all PDF pages, with headings and bold detected and marked up in markdown.
    """
    reader = PdfReader(pdf_path)
    all_text = []
    for page in reader.pages:
        # Try to detect fonts/styles if available through page.extract_text with details.
        # PyPDF2 does not natively provide font/style info in extract_text,
        # so we can do a simple heuristic: if a line is fully uppercase and short, call it a heading.
        page_text = page.extract_text()
        if not page_text:
            continue
        lines = page_text.splitlines()
        for line in lines:
            stripped_line = line.strip()
            # Heuristic: Heading if line is uppercase, alphanumeric, and short
            if (stripped_line.isupper() 
                and len(stripped_line.split()) <= 10 
                and any(c.isalpha() for c in stripped_line)):
                all_text.append(f'# {stripped_line}')
            # Heuristic: Bold if the line starts and ends with "**", or line is surrounded by whitespace and has >50% upper
            elif (len(stripped_line) > 2 and sum(1 for c in stripped_line if c.isupper()) / max(1,len(stripped_line)) > 0.5
                  and len(stripped_line.split()) < 15):
                all_text.append(f'**{stripped_line}**')
                #print(f'Bold: {stripped_line}')
            else:
                all_text.append(stripped_line)
    return "\n".join(all_text)

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=256):
    """
    Splits text into overlapping chunks of specified size.

    Args:
        text (str): Input text to split.
        chunk_size (int): Size of each chunk in characters.
        overlap (int): Number of characters to overlap between consecutive chunks.

    Yields:
        str: Chunked segment of the provided text.
    """
    # Calculate the step size between the start indices of consecutive chunks.
    # This is done by subtracting the overlap from the chunk size, indicating how much the window moves forward each iteration.
    step = chunk_size - overlap
    # Initialize the starting index for the first chunk.
    i = 0
    # Continue chunking until we have processed the entire input text.
    while i < len(text):
        # Define the start index for the current chunk (current position in the text).
        start = i
        # Define the end index for the current chunk (start + chunk_size), but does not exceed the text length.
        end = i + chunk_size
        # Slice the text from the start to the end index to obtain the current chunk.
        chunk = text[start:end]
        # Yield (i.e., provide) the current chunk to the calling context; useful for streaming or iteration.
        yield chunk
        # Move the start index forward by the step size, incorporating the desired overlap between chunks.
        i += step

def get_dir_size_mb(directory):
    """
    Computes the total size of all files in a directory, in megabytes (MB).

    Args:
        directory (str): Directory for which to compute total file size.

    Returns:
        float: Total size of all files in the directory, in MB.
    """
    total = 0
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total / (1024 * 1024)

if __name__ == '__main__':
    chunk_counter = 0
    for pdf_path in read_pdfs_from_dir(PDF_DIR):
        pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        print(f'Reading: {pdf_path}')
        print(f'Original PDF size: {pdf_size_mb:.2f} MB')
        text = extract_text_from_pdf(pdf_path)
        print(f'Extracted {len(text)} chars')
        for idx, chunk in enumerate(chunk_text(text, CHUNK_SIZE, overlap=256)):
            #print(f'Chunk {idx + 1} ({len(chunk)} chars)')
           # print(f'First 64 chars: {chunk[:64]!r}')
            # Embed the chunk
            embedding = model.encode(chunk)
            print(f'Embedding shape: {embedding.shape}')
            # Store in ChromaDB
            chunk_id = f"chunk_{chunk_counter}"
            collection.add(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": pdf_path, "chunk_index": idx}]
            )
            chunk_counter += 1
    print(f'Total chunks stored in ChromaDB: {chunk_counter}')
    # Size of the ChromaDB persist directory
    chromadb_size_mb = get_dir_size_mb(PERSIST_DIR)
    print(f'ChromaDB persist directory size: {chromadb_size_mb:.2f} MB')
