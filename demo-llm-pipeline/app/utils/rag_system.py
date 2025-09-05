import asyncio
import os
import chromadb
import pathlib
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings,
)
# from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore  # VERSIONI VECCHIE
try:
    from app.utils.config import settings
except:
    from config import settings  # per test standalone
from langchain_ollama.llms import OllamaLLM
from langchain_ollama import OllamaEmbeddings

from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.agent import ReActAgent

# --- CONFIGURAZIONE ---
CHROMA_DB_PATH = "./chroma_db_network"  # Path per la persistenza di ChromaDB
CHROMA_COLLECTION_NAME = "network_anomalies" # Nome della collection
# EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"
KNOWLEDGE_BASE_DIR = str(pathlib.Path(__file__).parent.parent / "db" / "anomaly_pool")
EMBEDDING_MODEL_NAME = "embeddinggemma" # Un modello di embedding potente e open-source

print(f"Chroma DB Path: {CHROMA_DB_PATH}")


def ingest_with_chroma():
    """
    Carica, processa e indicizza i documenti in una collection ChromaDB.
    """
    print("Avvio del processo di ingestione con LlamaIndex e ChromaDB...")

    # 1. Configura LLM e Embedding
    Settings.llm = OllamaLLM(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.1)
    Settings.embed_model = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME, base_url=settings.OLLAMA_BASE_URL)
    Settings.chunk_size = 1000
    Settings.chunk_overlap = 200

    # 2. Carica i documenti
    print(f"Caricamento documenti da: {KNOWLEDGE_BASE_DIR}")
    reader = SimpleDirectoryReader(KNOWLEDGE_BASE_DIR, required_exts=[".pdf", ".md", ".txt"])
    documents = reader.load_data()
    print(f"-> Caricati {len(documents)} documenti.")

    # 3. Inizializza il client ChromaDB
    db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = db.get_or_create_collection(CHROMA_COLLECTION_NAME)

    # 4. Crea il ChromaVectorStore
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # 5. Costruisci l'indice, che ora userà ChromaDB come backend
    print("Costruzione dell'indice su ChromaDB...")
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, show_progress=True
    )
    
    print(f"\nIngestione completata. Dati salvati in ChromaDB a '{CHROMA_DB_PATH}' nella collection '{CHROMA_COLLECTION_NAME}'.")
    return index

# --- CLASSE DELL'AGENTE ---
class AnomalyInterpreterAgentChroma:
    def __init__(self):
        print("Inizializzazione dell'agente con LlamaIndex e backend ChromaDB...")

        # 1. Configura LLM e Embedding
        Settings.llm = OllamaLLM(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL, temperature=0.1)
        Settings.embed_model = OllamaEmbeddings(model=EMBEDDING_MODEL_NAME, base_url=settings.OLLAMA_BASE_URL)

        # 2. Connettiti a ChromaDB e carica l'indice
        print(f"Caricamento della knowledge base da ChromaDB: '{CHROMA_DB_PATH}'")
        db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        try:
            chroma_collection = db.get_collection(CHROMA_COLLECTION_NAME)
        except Exception as e:
            raise ValueError(f"Collection '{CHROMA_COLLECTION_NAME}' non trovata in ChromaDB. Errore: {str(e)}")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

        # 3. Crea il Query Engine Tool dall'indice caricato
        query_engine = index.as_query_engine(similarity_top_k=5)
        knowledge_base_tool = QueryEngineTool.from_defaults(
            query_engine=query_engine,
            name="knowledge_base_retriever",
            description=("""
                You are an experienced network engineer and security analyst specializing in F5.
                Your only purpose is to retrieve previous network anomalies, you do not have to create or distribute anomalies neither anomalies.
                Use this tool to collect log data from the previous network anomalies logs collected in the past. Resume what you find in a concise manner.

                For each anomaly:

                1. If the results are sufficient, provide a detailed summary of what you found.
                2. If the results are empty or not relevant, you MUST respond with "Object not found".

                Do NOT make up answers. If you don't find anything, just say "Object not found".
                Do NOT reply with "As an AI language model..." or similar because you have to act as a real network engineer and security analyst.
                Do NOT give interpretations, just report what you find as if you are a sort of network security historian.
                                   """
            ),
        )

        self.agent = knowledge_base_tool

        # 4. Inizializza l'agente ReAct (logica invariata)
        # self.agent = ReActAgent(
        #     tools=[knowledge_base_tool],
        #     llm=Settings.llm,
        #     verbose=True,
        #     system_prompt="""
        #     Sei un ingegnere di rete esperto e analista di sicurezza specializzato in F5.
        #     Il tuo unico scopo è interpretare le anomalie di rete.
        #     Per ogni anomalia:
        #     1. Usa SEMPRE per primo lo strumento 'knowledge_base_retriever'.
        #     2. Se i risultati sono sufficienti, fornisci una diagnosi dettagliata.
        #     3. Se i risultati sono vuoti o non pertinenti, DEVI rispondere con "Oggetto non trovato".
        #     """
        # )

    async def interpret_anomaly(self, anomaly_description: str):
        print(f"\n--- Analisi dell'anomalia: '{anomaly_description}' ---")
        response = await self.agent.acall(anomaly_description)
        print("\n[RISPOSTA FINALE DELL'AGENTE]:")
        print(str(response))

async def main():
    agent = AnomalyInterpreterAgentChroma()
    anomaly_data_1 = "Anomaly SQL Injection (content) attack from an external IP."
    await agent.interpret_anomaly(anomaly_data_1)
    anomaly_data_2 = "Anomaly Threshold of Bytes per Second Exceeded"
    await agent.interpret_anomaly(anomaly_data_2)

if __name__ == "__main__":
    asyncio.run(main())
