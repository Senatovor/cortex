from langchain_ollama import OllamaEmbeddings
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from loguru import logger
import asyncio

from backend.config import config


class VectorStoreManager:
    """
    Менеджер для работы с векторными хранилищами Qdrant.

    Управляет подключением к Qdrant, созданием эмбеддингов через Ollama
    и инициализацией коллекций. Поддерживает работу с несколькими коллекциями
    одновременно, кэшируя их в памяти.

    Attributes:
        embeddings (OllamaEmbeddings | None): Модель для создания эмбеддингов
        qdr_client (QdrantClient | None): Клиент для подключения к Qdrant
        vector_stores (dict[str, QdrantVectorStore]): Словарь инициализированных
            векторных хранилищ, где ключ - имя коллекции

    Args:
        embeddings (OllamaEmbeddings | None, optional):
            Готовая модель эмбеддингов. Если не указана, будет создана при init().
            Defaults to None.
        qdr_client (QdrantClient | None, optional):
            Готовый клиент Qdrant. Если не указан, будет создан при init().
            Defaults to None.
    """
    def __init__(
            self,
            embeddings: OllamaEmbeddings | None = None,
            qdr_client: QdrantClient | None = None,
    ):
        self.embeddings = embeddings
        self.qdr_client = qdr_client
        self.vector_stores: dict[str, QdrantVectorStore] = {}

    async def init(self):
        """
        Асинхронная инициализация менеджера векторной БД.

        Создает подключение к Ollama для эмбеддингов, инициализирует клиент Qdrant,
        проверяет наличие и создает при необходимости все коллекции из конфигурации.

        Raises:
            RuntimeError: Если не удалось инициализировать менеджер.
                          Возникает при любых ошибках подключения или создания коллекций.
        """
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
        """Закрывает соединение с клиентом Qdrant."""
        if self.qdr_client:
            self.qdr_client.close()

    def get_vector_store(self, collection_name: str) -> QdrantVectorStore:
        """
        Возвращает векторное хранилище для указанной коллекции.

        Args:
            collection_name (str): Имя коллекции, для которой нужно получить хранилище.

        Returns:
            QdrantVectorStore: Инициализированное векторное хранилище для работы с коллекцией.

        Raises:
            KeyError: Если коллекция с указанным именем не была инициализирована.
        """
        return self.vector_stores[collection_name]


vector_manager = VectorStoreManager()
asyncio.run(vector_manager.init())
