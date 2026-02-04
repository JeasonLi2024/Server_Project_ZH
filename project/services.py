import os
import json
import logging
from openai import OpenAI
from django.conf import settings
from langchain_core.documents import Document
from pymilvus import connections, Collection, utility, DataType, FieldSchema, CollectionSchema

logger = logging.getLogger(__name__)

# 配置 Milvus 连接
MILVUS_HOST = os.getenv('MILVUS_HOST', 'localhost')
MILVUS_PORT = os.getenv('MILVUS_PORT', '19530')
MILVUS_ALIAS = 'default'

# 向量集合名称
COLLECTION_EMBEDDINGS = 'project_embeddings'
COLLECTION_RAW_DOCS = 'project_raw_docs'

# 默认使用 DashScope text-embedding-v4
DEFAULT_EMBEDDING_MODEL = "text-embedding-v4"
DEFAULT_EMBEDDING_DIM = 1536

class EmbeddingService:
    """
    统一的向量化服务类，提供文本切块和向量化功能
    统一使用 DashScope text-embedding-v4 模型 (Local Version for Server_Project_ZH/project)
    """
    
    @staticmethod
    def get_dashscope_client():
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            # 尝试从 settings 获取 (如果有)
            api_key = getattr(settings, "DASHSCOPE_API_KEY", None)
            
        if not api_key:
             # 如果环境变量和settings都没有，可能需要报错或fallback
             # 这里我们先抛出错误，因为这是核心依赖
             raise ValueError("DASHSCOPE_API_KEY not found in environment or settings")
             
        return OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    @staticmethod
    def split_text(text, max_char_per_chunk=300, overlap=50):
        # 保持与 langchain-text-splitters 逻辑一致
        sentences = re.split(r'[\n\u3002\uff1f\uff01]', text)  
        chunks = []
        current = ""

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current) + len(sent) <= max_char_per_chunk:
                current += sent + "\u3002"  # 加个句号
            else:
                if current:
                    chunks.append(current.strip())
                current = sent + "\u3002"

        if current:
            chunks.append(current.strip())

        # 重叠处理
        final_chunks = []
        for i in range(len(chunks)):
            chunk = chunks[i]
            if i > 0 and overlap > 0:
                prev = chunks[i - 1]
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                chunk = overlap_text + chunk
            final_chunks.append(chunk)

        logger.info(f"[Chunking] 切分为 {len(final_chunks)} 段")
        return final_chunks
    
    @staticmethod
    def get_embeddings(texts, use_cache=True):
        from django.core.cache import cache
        if not texts:
            return []
            
        # 如果使用缓存，先检查缓存
        if use_cache:
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cache_key = f"embedding:v4:{hash(text)}" 
                cached = cache.get(cache_key)
                if cached:
                    cached_embeddings.append((i, cached))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # 如果所有文本都有缓存，直接返回
            if not uncached_texts:
                result = [None] * len(texts)
                for i, embedding in cached_embeddings:
                    result[i] = embedding
                return result
            
            # 获取未缓存的向量
            new_embeddings = EmbeddingService._fetch_embeddings(uncached_texts)
            
            # 缓存新获取的向量
            for i, text in enumerate(uncached_texts):
                if i < len(new_embeddings):
                    cache_key = f"embedding:v4:{hash(text)}"
                    cache.set(cache_key, new_embeddings[i], timeout=3600)  # 缓存1小时
            
            # 合并结果
            result = [None] * len(texts)
            for i, embedding in cached_embeddings:
                result[i] = embedding
            for i, idx in enumerate(uncached_indices):
                if i < len(new_embeddings):
                    result[idx] = new_embeddings[i]
            
            return result
        else:
            return EmbeddingService._fetch_embeddings(texts)
    
    @staticmethod
    def _fetch_embeddings(texts):
        try:
            client = EmbeddingService.get_dashscope_client()
            
            # 批量处理
            batch_size = 10
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                try:
                    response = client.embeddings.create(
                        model=DEFAULT_EMBEDDING_MODEL,
                        input=batch,
                        dimensions=DEFAULT_EMBEDDING_DIM
                    )
                    
                    batch_embeddings = [None] * len(batch)
                    for item in response.data:
                         if item.index < len(batch):
                             batch_embeddings[item.index] = item.embedding
                             
                    all_embeddings.extend(batch_embeddings)
                    
                except Exception as batch_error:
                    logger.error(f"[Embedding Batch ERROR] {batch_error}")
                    all_embeddings.extend([None] * len(batch))
            
            final_embeddings = []
            for emb in all_embeddings:
                if emb is None:
                    final_embeddings.append([0.0] * DEFAULT_EMBEDDING_DIM)
                else:
                    final_embeddings.append(emb)

            logger.info(f"[Embedding] 成功获取 {len(final_embeddings)} 个向量 (v4)")
            return final_embeddings

        except Exception as e:
            logger.error(f"[Embedding ERROR] {e}")
            return [[0.0] * DEFAULT_EMBEDDING_DIM for _ in texts]
    
    @staticmethod
    def get_single_embedding(text, use_cache=True):
        embeddings = EmbeddingService.get_embeddings([text], use_cache=use_cache)
        return embeddings[0] if embeddings else [0.0] * DEFAULT_EMBEDDING_DIM

def generate_embedding(text):
    """
    使用 text-embedding-v4 生成向量 (Wrapper around local EmbeddingService)
    """
    if not text:
        return []
    
    try:
        return EmbeddingService.get_single_embedding(text)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return []

def ensure_milvus_connection():
    try:
        connections.connect(alias=MILVUS_ALIAS, host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception as e:
        logger.error(f"Failed to connect to Milvus: {e}")

def get_or_create_collection(collection_name, dim=1536):
    ensure_milvus_connection()
    
    if utility.has_collection(collection_name):
        return Collection(collection_name)
    
    # 定义 Schema
    if collection_name == COLLECTION_EMBEDDINGS:
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="project_id", dtype=DataType.INT64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535)
        ]
    elif collection_name == COLLECTION_RAW_DOCS:
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="project_id", dtype=DataType.INT64),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="chunk_index", dtype=DataType.INT64)
        ]
    else:
        raise ValueError(f"Unknown collection: {collection_name}")
        
    schema = CollectionSchema(fields, f"{collection_name} schema")
    collection = Collection(collection_name, schema)
    
    # 创建索引
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    collection.load()
    return collection

def sync_requirement_vectors(requirement):
    """
    同步需求数据到 Milvus (Track 2: Semantic)
    仅当状态为有效状态时同步
    """
    # 有效状态列表
    VALID_STATUSES = ['under_review', 'in_progress', 'completed', 'paused']
    
    # 如果是草稿或审核失败，应当删除向量（如果存在），或者不进行更新
    # 这里策略是：如果是非有效状态，执行删除操作，确保不被推荐
    if requirement.status not in VALID_STATUSES:
        delete_requirement_vectors(requirement.id)
        return

    try:
        # 1. 准备文本
        # 组合 Title + Brief + Description + Tags
        tags1 = [t.value for t in requirement.tag1.all()]
        tags2 = [t.post for t in requirement.tag2.all()]
        
        full_text = f"Title: {requirement.title}\nBrief: {requirement.brief}\nDescription: {requirement.description}\nTags: {', '.join(tags1 + tags2)}"
        
        # 2. 生成向量
        vector = generate_embedding(full_text)
        if not vector:
            logger.warning(f"Failed to generate embedding for requirement {requirement.id}")
            return

        # 3. 写入 Milvus
        # 先删除旧的（防止重复）
        delete_requirement_vectors(requirement.id, collection_names=[COLLECTION_EMBEDDINGS])
        
        collection = get_or_create_collection(COLLECTION_EMBEDDINGS)
        
        data = [
            [requirement.id],  # project_id
            [vector],          # vector
            [full_text[:65535]]  # content (Use full text up to 65535)
        ]
        
        collection.insert(data)
        collection.flush() # Ensure data is written
        logger.info(f"Successfully synced vectors for requirement {requirement.id}")
        
    except Exception as e:
        logger.error(f"Error syncing vectors for requirement {requirement.id}: {e}")

from langchain_text_splitters import RecursiveCharacterTextSplitter
import fitz  # PyMuPDF
import docx  # python-docx

def extract_text_from_file(file_path):
    """
    根据文件扩展名提取文本
    支持: .pdf, .docx, .doc (视作docx尝试或文本), .txt, .md
    """
    if not os.path.exists(file_path):
        return ""
    
    try:
        ext = os.path.splitext(file_path)[1].lower()
        text = ""
        
        if ext == '.pdf':
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
                    
        elif ext in ['.docx', '.doc']:
            # 注意: .doc 实际上 python-docx 不支持旧版二进制 Word，但如果是 docx 改名则支持
            # 如果是纯文本内容，尝试用 python-docx 读取
            try:
                doc = docx.Document(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
            except Exception:
                # 兜底：尝试作为文本读取
                logger.warning(f"Failed to read {file_path} with python-docx, trying text fallback")
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                    
        else:
            # 默认尝试文本读取 (txt, md, etc.)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
                
        return text
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {e}")
        return ""

def sync_raw_docs_auto(requirement):
    """
    自动判断并同步 Raw Docs (文档切片)
    1. 检查是否有关联文件
    2. 如果有文件 -> 提取所有文件内容 -> 批量切片 -> 存入 Milvus
    3. 如果无文件 -> 使用 Description + Metadata -> 切片 -> 存入 Milvus
    
    注意：此函数会先执行删除操作，确保数据一致性 (Atomic overwrite per requirement)
    """
    if not requirement or not requirement.id:
        return

    # Re-fetch requirement to ensure we have the latest relation state (especially in async threads)
    try:
        from .models import Requirement
        requirement = Requirement.objects.get(id=requirement.id)
    except Exception as e:
        logger.error(f"Requirement {requirement.id} not found in sync_raw_docs_auto: {e}")
        return

    # 有效状态列表
    VALID_STATUSES = ['under_review', 'in_progress', 'completed', 'paused']
    if requirement.status not in VALID_STATUSES:
        delete_requirement_vectors(requirement.id, [COLLECTION_RAW_DOCS])
        return

    try:
        # 1. 获取所有关联文件 (过滤文件夹)
        # 注意: 需要确保 files 关联已保存
        valid_files = []
        if requirement.pk:
            for f in requirement.files.all():
                if not f.is_folder and f.real_path:
                     valid_files.append(f)
        
        logger.info(f"Requirement {requirement.id} checking files: found {len(valid_files)} valid files.")
        
        full_text_content = ""
        
        # 2. 提取内容
        if valid_files:
            logger.info(f"Requirement {requirement.id} has {len(valid_files)} files. Extracting text...")
            for file_obj in valid_files:
                # 构建绝对路径
                if os.path.isabs(file_obj.real_path):
                    file_abs_path = file_obj.real_path
                else:
                    file_abs_path = os.path.join(settings.MEDIA_ROOT, file_obj.real_path)
                file_text = extract_text_from_file(file_abs_path)
                if file_text:
                    full_text_content += f"\n\n--- File: {file_obj.name} ---\n{file_text}"
        
        # 3. 如果没有文件内容 (无文件或提取失败)，使用 Metadata 兜底
        if not full_text_content.strip():
            logger.info(f"Requirement {requirement.id} has no file content. Using description fallback.")
            tags1 = [t.value for t in requirement.tag1.all()]
            tags2 = [t.post for t in requirement.tag2.all()]
            full_text_content = f"Title: {requirement.title}\nBrief: {requirement.brief}\nDescription: {requirement.description}"
            if tags1 or tags2:
                full_text_content += f"\nTags: {', '.join(tags1 + tags2)}"
        
        # 4. 执行同步 (切片 + 向量化 + 存储)
        # 复用 sync_raw_docs_from_text 的逻辑，因为它本质上就是处理一段长文本
        sync_raw_docs_from_text(requirement.id, full_text_content)
        
    except Exception as e:
        logger.error(f"Error in sync_raw_docs_auto for requirement {requirement.id}: {e}")

def sync_raw_docs_from_text(requirement_id, text):
    """
    当没有文件时，将纯文本描述切片并存入 project_raw_docs
    """
    if not text or not requirement_id:
        return
        
    try:
        # 1. 文本切片
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", "。", "！", "!", ".", " "]
        )
        chunks = splitter.split_text(text)
        
        if not chunks:
            return

        # 2. 生成向量 (使用 EmbeddingService 批量处理)
        # 过滤太短的
        valid_chunks = [chunk for chunk in chunks if len(chunk.strip()) >= 10]
        
        if not valid_chunks:
            return

        # 批量获取向量 (自带缓存和批量请求)
        vectors = EmbeddingService.get_embeddings(valid_chunks, use_cache=True)
        
        # 过滤获取失败的向量 (None 或 空列表)
        final_vectors = []
        final_chunks = []
        indices = []
        
        for i, vec in enumerate(vectors):
            if vec and len(vec) > 0:
                final_vectors.append(vec)
                final_chunks.append(valid_chunks[i][:65535])
                indices.append(i)
        
        if not final_vectors:
            return
            
        # 3. 存入 Milvus
        # 先删除旧的
        delete_requirement_vectors(requirement_id, [COLLECTION_RAW_DOCS])
        
        collection = get_or_create_collection(COLLECTION_RAW_DOCS)
        
        pids = [requirement_id] * len(final_vectors)
        data = [
            pids,
            final_vectors,
            final_chunks,
            indices
        ]
        
        collection.insert(data)
        collection.flush()
        logger.info(f"Synced {len(final_vectors)} text chunks for requirement {requirement_id}")
        
    except Exception as e:
        logger.error(f"Error syncing raw text docs for requirement {requirement_id}: {e}")

def delete_requirement_vectors(requirement_id, collection_names=None):
    """
    删除指定需求的所有向量数据
    """
    ensure_milvus_connection()
    
    if collection_names is None:
        collection_names = [COLLECTION_EMBEDDINGS, COLLECTION_RAW_DOCS]
        
    for name in collection_names:
        try:
            if utility.has_collection(name):
                collection = Collection(name)
                expr = f"project_id == {requirement_id}"
                collection.delete(expr)
                logger.info(f"Deleted vectors for requirement {requirement_id} in {name}")
        except Exception as e:
            logger.error(f"Error deleting vectors for requirement {requirement_id} in {name}: {e}")
