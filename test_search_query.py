import chromadb
from sentence_transformers import SentenceTransformer

PERSIST_DIR = './vector-data'


def load_persisted_collection(collection_name: str = 'pdf_chunks', persist_dir: str = PERSIST_DIR):
    """
    Loads a ChromaDB collection from the given persistent directory.

    Args:
        collection_name (str, optional): Name of the collection to load. Defaults to 'pdf_chunks'.
        persist_dir (str, optional): Path to the directory where persistent data is stored. Defaults to PERSIST_DIR.

    Returns:
        chromadb.api.models.Collection.Collection: The loaded ChromaDB collection object.
    """
    persistent_client = chromadb.PersistentClient(path=persist_dir)
    collection = persistent_client.get_collection(collection_name)
    print(f"Number of documents in the collection: {collection.count()}")
    return collection


# Initialize collection and model at module level (loaded once when module is imported)
print("Initializing ChromaDB collection and embedding model...")
collection = load_persisted_collection()
print(f"Loaded collection: {collection.name}")

# Use the SAME SentenceTransformer model as during ingestions
model = SentenceTransformer('intfloat/multilingual-e5-base')
print("Embedding model loaded successfully.\n")


def semantic_search(query: str, n_results: int = 5, min_similarity: float = 0.1) -> list:
    """
    Performs semantic search on the ChromaDB collection and returns matching documents.
    
    This function can be used as a tool by the Gemini agent to search through
    the ingested PDF documents.

    Args:
        query (str): The search query string.
        n_results (int, optional): Number of results to return. Defaults to 5.
        min_similarity (float, optional): Minimum similarity score threshold (0-1). Defaults to 0.1.

    Returns:
        list: List of dictionaries, each containing:
            - 'document' (str): The document text content
            - 'metadata' (dict): Metadata including source file and chunk index
            - 'similarity' (float): Similarity score (0-1, higher is better)
    """
    # Add query prefix required by multilingual-e5-base model
    prefixed_query = f"query: {query}"
    query_embedding = model.encode(prefixed_query)
    
    # Perform semantic search
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    
    # Extract results
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    scores_or_distances = results.get('distances', results.get('scores', [[]]))[0]
    
    # Build result list
    search_results = []
    for i in range(len(documents)):
        doc = documents[i]
        meta = metadatas[i]
        score = scores_or_distances[i]
        
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
    # Example usage: Interactive semantic search
    while True:
        query_text = input("Enter your search query (or type 'exit' to quit): ").strip()
        if query_text.lower() in ('exit', 'quit'):
            print("Exiting semantic search.")
            break
        
        print(f"\nPerforming semantic search for: {query_text}")
        results = semantic_search(query_text, n_results=3, min_similarity=0.1)
        
        if results:
            print(f"\nFound {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"Result {i} (similarity: {result['similarity']:.4f}):")
                print(f"Source: {result['metadata'].get('source', 'Unknown')}")
                print(f"Content: {result['document'][:300]}...")
                print("---")
        else:
            print("No results found matching the query.")
        print()
