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

if __name__ == '__main__':  # test_search_query.py
    # Load the persisted collection
    collection = load_persisted_collection()
    print(f"Loaded collection: {collection.name}")

    # Use the SAME SentenceTransformer model as during ingestions
    model = SentenceTransformer('intfloat/multilingual-e5-base')

    # Perform semantic search over documents present in the Chroma collection
    query_text = "Tetra packs of Whiskey dangerous?"  # Replace this with your search query as needed
    print(f"Performing semantic search for: {query_text}")
    query_embedding = model.encode(query_text)

    # Retrieve top 3 most similar documents from the collection
    results = collection.query(
        query_embeddings=[query_embedding],  # Pass embeddings as list in latest chromadb API
        n_results=3
    )

    # Access the retrieved documents and their metadata
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    scores_or_distances = results.get('distances', results.get('scores', [[]]))[0]
    for i in range(len(documents)):
        doc = documents[i]
        meta = metadatas[i]
        score = scores_or_distances[i]
        # Chroma returns smaller distances for closer match, but (in some configs) also "scores" as similarity
        # We'll let 'score' be a similarity value between 0 and 1 if available, otherwise invert distance
        similarity = None
        if 'scores' in results:  # cosine similarity (1==identical)
            similarity = score
        elif 'distances' in results:  # distance; 0 is perfect
            similarity = 1 - score  # crude conversion for cosine; may differ for other metrics

        # consider only >80% similarity
        if similarity is not None and similarity > 0.1:
            print(f"Result {i+1}:")
            print(doc)
            print(f"Metadata: {meta}")
            print(f"Similarity score: {similarity:.2f}")
            print("---")
