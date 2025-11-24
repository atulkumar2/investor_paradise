"""Semantic search utilities over a ChromaDB collection of PDF chunks.

Lazily initializes the Chroma collection and embedding model on first use.
The persist directory can be overridden via the PERSIST_DIR environment
variable or by calling init_search_resources().
"""

import logging
import os
from types import SimpleNamespace
from typing import cast

import chromadb
from sentence_transformers import SentenceTransformer

DEFAULT_PERSIST_DIR = './vector-data'
DEFAULT_COLLECTION = 'pdf_chunks'
DEFAULT_MODEL = 'intfloat/multilingual-e5-base'

_state = SimpleNamespace(collection=None, model=None)
_model = None
logger = logging.getLogger("semantic_search")


def load_persisted_collection(
        collection_name: str = DEFAULT_COLLECTION,
        persist_dir: str = DEFAULT_PERSIST_DIR,
):
    """
    Loads a ChromaDB collection from the given persistent directory.

    Args:
        collection_name (str, optional): Name of the collection to load.
        persist_dir (str, optional): Path to directory where Chroma persists data.

    Returns:
        chromadb.api.models.Collection.Collection: Loaded ChromaDB collection.
    """
    persistent_client = chromadb.PersistentClient(path=persist_dir)
    collection = persistent_client.get_collection(collection_name)
    logger.info(
        "Collection '%s' count: %d",
        collection_name,
        collection.count(),
    )
    return collection

def init_search_resources(
    persist_dir: str | None = None,
    collection_name: str = DEFAULT_COLLECTION,
    model_name: str = DEFAULT_MODEL,
) -> None:
    """Initialize and cache the Chroma collection and embedding model."""
    if persist_dir is None:
        persist_dir = os.environ.get('PERSIST_DIR', DEFAULT_PERSIST_DIR)
    _state.collection = load_persisted_collection(
        collection_name=collection_name, persist_dir=persist_dir
    )
    _state.model = SentenceTransformer(model_name)


def semantic_search(
        query: str,
        n_results: int = 5,
        min_similarity: float = 0.1,
) -> list:
    """
    Performs semantic search on the ChromaDB collection and returns matching documents.

    This function can be used as a tool by the Gemini agent to search through
    the ingested PDF documents.

    Args:
        query (str): The search query string.
        n_results (int, optional): Number of results to return. Defaults to 5.
        min_similarity (float, optional): Minimum similarity threshold (0-1).

    Returns:
        list: List of dictionaries, each containing:
            - 'document' (str): The document text content
            - 'metadata' (dict): Metadata including source file and chunk index
            - 'similarity' (float): Similarity score (0-1, higher is better)
    """
    # Ensure resources are initialized
    # Ensure resources are initialized
    if _state.collection is None or _state.model is None:
        init_search_resources()

    # Add query prefix required by multilingual-e5-base model
    prefixed_query = f"query: {query}"
    query_embedding = _state.model.encode(prefixed_query)  # type: ignore[union-attr]
    # Convert to plain list[float] if needed for Chroma types
    if hasattr(query_embedding, 'tolist'):
        query_embedding = query_embedding.tolist()
    qe_list = cast(list[float], query_embedding)

    # Perform semantic search
    results = _state.collection.query(  # type: ignore[union-attr]
        query_embeddings=[qe_list],
        n_results=n_results
    )
    # Extract results
    if not results or not results.get('documents'):
        return []
    documents = results['documents'][0]  # type: ignore[index]
    metadatas = results['metadatas'][0]  # type: ignore[index]
    scores_or_distances = results.get('distances', results.get('scores', [[]]))[0]  # type: ignore[index]

    # Build result list
    search_results = []
    for idx, (doc, meta, score) in enumerate(
        zip(documents, metadatas, scores_or_distances)
    ):

        # Calculate similarity score
        if 'scores' in results:  # cosine similarity (1==identical)
            similarity = score
        elif 'distances' in results:  # distance; 0 is perfect
            similarity = 1 - score  # convert distance to similarity
        else:
            similarity = None

        # Filter by minimum similarity threshold
        if similarity is not None and similarity >= min_similarity:
            search_results.append({
                'document': doc,
                'metadata': meta,
                'similarity': round(similarity, 4)
            })

    return search_results

if __name__ == '__main__':
    # Configure logging only for direct script execution
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        )

    init_search_resources()
    # Example usage: Interactive semantic search
    while True:
        query_text = input("Enter your search query (or type 'exit' to quit): ").strip()
        if query_text.lower() in ('exit', 'quit'):
            logger.info("Exiting semantic search.")
            break

        logger.info("Performing semantic search for: %s", query_text)
        results = semantic_search(query_text, n_results=3, min_similarity=0.1)

        if results:
            logger.info("Found %d results:", len(results))
            for i, result in enumerate(results, 1):
                logger.info(
                    "Result %d (similarity: %.4f)", i, result['similarity']
                )
                logger.info(
                    "Source: %s",
                    result['metadata'].get('source', 'Unknown'),
                )
                logger.info("Content: %s...", result['document'][:300])
        else:
            logger.info("No results found matching the query.")
