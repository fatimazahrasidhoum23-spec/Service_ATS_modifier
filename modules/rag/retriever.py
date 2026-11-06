# modules/rag/retriever.py

from sentence_transformers import SentenceTransformer
import chromadb
import os

class RAGRetriever:

    def __init__(self):
        print("Initialisation du RAG...")

        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

        # Mode local — pas besoin de serveur ChromaDB séparé
        self.client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "/app/chroma_data"))

        self.collection = self.client.get_or_create_collection(
            name="ats_knowledge",
            metadata={"hnsw:space": "cosine"}
        )

        print("RAG initialise !")

    def index_knowledge_base(self, documents: list[str]):
        print(f"Indexation de {len(documents)} documents...")

        try:
            self.client.delete_collection("ats_knowledge")
            self.collection = self.client.get_or_create_collection(
                name="ats_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
        except:
            pass

        batch_size = 50
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            embeddings = self.model.encode(batch).tolist()
            self.collection.add(
                documents=batch,
                embeddings=embeddings,
                ids=[f"doc_{i + j}" for j in range(len(batch))]
            )

        print(f"{len(documents)} documents indexes !")

    def get_context(self, query: str, k: int = 5) -> str:
        query_embedding = self.model.encode([query]).tolist()

        count = self.collection.count()
        if count == 0:
            return ""

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(k, count)
        )

        if results["documents"] and results["documents"][0]:
            return "\n".join(results["documents"][0])

        return ""

    def get_skills_context(self, skills: list[str]) -> str:
        contexts = []
        for skill in skills:
            context = self.get_context(skill, k=2)
            if context:
                contexts.append(context)
        return "\n".join(set(contexts))

    def is_indexed(self) -> bool:
        try:
            return self.collection.count() > 0
        except:
            return False
