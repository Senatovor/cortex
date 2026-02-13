from langchain_ollama import OllamaEmbeddings
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from loguru import logger

from backend.config import config


class VectorStoreManager:
    def __init__(
            self,
            embeddings: OllamaEmbeddings | None = None,
            qdr_client: QdrantClient | None = None,
    ):
        self.embeddings = embeddings
        self.qdr_client = qdr_client
        self.vector_stores: dict[str, QdrantVectorStore] = {}

    async def init(self):
        logger.info('Инициализация менеджера векторной БД...')
        try:
            logger.info('Создание embeddings...')
            self.embeddings = OllamaEmbeddings(
                model=config.rag_config.EMBEDDINGS_MODEL_NAME,
                base_url=config.rag_config.MODEL_HOST,
            )
            logger.info('Создание qdr_client...')
            self.qdr_client = QdrantClient(
                host=config.rag_config.QDRANT_HOST,
                port=config.rag_config.QDRANT_PORT
            )
            logger.info('Создание коллекций...')
            for collection_name in config.rag_config.LIST_COLLECTION:
                if collection_name not in self.vector_stores:
                    if not self.qdr_client.collection_exists(collection_name):
                        self.qdr_client.create_collection(
                            collection_name=collection_name,
                            vectors_config=VectorParams(size=config.rag_config.VECTOR_SIZE, distance=Distance.COSINE)
                        )
                    self.vector_stores[collection_name] = QdrantVectorStore(
                        client=self.qdr_client,
                        collection_name=collection_name,
                        embedding=self.embeddings,
                    )
        except Exception as e:
            logger.error(f"Ошибка инициализации менеджера векторной БД: {e}")
            raise RuntimeError(f"Не удалось инициализировать менеджер векторной БД: {e}") from e

    async def close(self):
        if self.qdr_client:
            self.qdr_client.close()

    def get_vector_store(self, collection_name: str) -> QdrantVectorStore:
        return self.vector_stores[collection_name]


vector_manager = VectorStoreManager()
