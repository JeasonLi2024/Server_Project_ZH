# import fitz  # PyMuPDF
# import re
# import requests
# import json
# from pymilvus import connections, Collection, utility

# # ========== 配置 ==========
# MILVUS_HOST = "100.116.251.123"
# MILVUS_PORT = "19530"
# COLLECTION_NAME = "enterprise_vectors"

# EMBEDDING_URL = "http://100.116.251.123:11434/api/embed"  
# EMBEDDING_MODEL = "bge-m3:567m"
# EMBEDDING_DIM = 1024

# # ========== PDF提取 ==========
# def extract_and_clean_pdf_text(pdf_path):
#     doc = fitz.open(pdf_path)
#     full_text = ""
#     for page in doc:
#         full_text += page.get_text()
#     doc.close()

#     cleaned_text = re.sub(r'[ \t]+', ' ', full_text)
#     return cleaned_text.strip()

# # 文本切块（优化：按段/句切，每段约200~300字）
# def split_text(text, max_char_per_chunk=300, overlap=50):
#     sentences = re.split(r'[\n\u3002\uff1f\uff01]', text)  
#     chunks = []
#     current = ""

#     for sent in sentences:
#         sent = sent.strip()
#         if not sent:
#             continue
#         if len(current) + len(sent) <= max_char_per_chunk:
#             current += sent + "\u3002"  #加个句号
#         else:
#             if current:
#                 chunks.append(current.strip())
#             current = sent + "\u3002"

#     if current:
#         chunks.append(current.strip())

#     # 重叠处理（按字符）
#     final_chunks = []
#     for i in range(len(chunks)):
#         chunk = chunks[i]
#         if i > 0 and overlap > 0:
#             prev = chunks[i - 1]
#             overlap_text = prev[-overlap:] if len(prev) > overlap else prev
#             chunk = overlap_text + chunk
#         final_chunks.append(chunk)

#     print(f"[Chunking] 切分为 {len(final_chunks)} 段，每段约 {max_char_per_chunk} 字")
#     return final_chunks

# # 批量获取向量
# def get_embeddings(texts):
#     try:
#         payload = {"model": EMBEDDING_MODEL, "input": texts}
#         headers = {"Content-Type": "application/json"}
#         response = requests.post(EMBEDDING_URL, headers=headers, data=json.dumps(payload))
#         response.raise_for_status()
#         result = response.json()
#         embeddings = result.get("embeddings", [])

#         if not embeddings or len(embeddings) != len(texts):
#             raise ValueError("返回的 embedding 数量与输入文本数量不匹配")

#         for i, emb in enumerate(embeddings):
#             if not isinstance(emb, list) or len(emb) != EMBEDDING_DIM:
#                 raise ValueError(f"第 {i} 个 embedding 长度错误：{len(emb)}，应为 {EMBEDDING_DIM}")

#         return embeddings

#     except Exception as e:
#         print(f"[Embedding ERROR] {e}")
#         return [[0.0] * EMBEDDING_DIM for _ in texts]
        
# # 清洗 JSON 中可能导致序列化失败的非法字符
# # def clean_for_json(val):
# #     if isinstance(val, dict):
# #         return {k: clean_for_json(v) for k, v in val.items()}
# #     elif isinstance(val, list):
# #         return [clean_for_json(v) for v in val]
# #     elif isinstance(val, str):
# #         # 删除 ASCII 控制字符 (0x00-0x1F) 和 DEL (0x7F)
# #         val = re.sub(r'[\x00-\x1F\x7F]', '', val)
# #         return val
# #     else:
# #         return str(val)

# # ========== 插入 Milvus ==========
# def insert_into_milvus(chunks, pid):
#     if not utility.has_collection(COLLECTION_NAME):
#         raise ValueError(f"Collection '{COLLECTION_NAME}' 不存在，请先创建")

#     collection = Collection(COLLECTION_NAME)

#     try:
#         collection.delete(f"Pid == {pid}")
#         print(f"[Milvus] 删除旧数据，Pid={pid}")
#     except Exception as e:
#         print(f"[Milvus ERROR] 删除失败: {e}")

#     embeddings = get_embeddings(chunks)
#     pids = [pid] * len(chunks)
#     chunk_numbers = list(range(len(chunks)))
#     texts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
#     add_data1s = [{} for _ in chunks]
#     add_data2s = [{} for _ in chunks]

#     records = [embeddings, pids, chunk_numbers, texts, add_data1s, add_data2s]

#     try:
#         collection.insert(records)
#         print(f"[Milvus] 插入成功，共 {len(chunks)} 条记录")
#     except Exception as e:
#         print(f"[Milvus ERROR] 插入失败: {e}")
# # def insert_into_milvus(chunks, pid):
# #     if not utility.has_collection(COLLECTION_NAME):
# #         raise ValueError(f"Collection '{COLLECTION_NAME}' 不存在，请先创建")

# #     collection = Collection(COLLECTION_NAME)

# #     # 删除旧数据
# #     try:
# #         collection.delete(f"Pid == {pid}")
# #         print(f"[Milvus] 删除旧数据，Pid={pid}")
# #     except Exception as e:
# #         print(f"[Milvus ERROR] 删除失败: {e}")

# #     # 获取向量
# #     embeddings = get_embeddings(chunks)

# #     pids = [pid] * len(chunks)
# #     chunk_numbers = list(range(len(chunks)))

# #     # 先构造文本字段
# #     texts = [{"content": chunk} for chunk in chunks]
# #     texts = [clean_for_json(t) for t in texts]

# #     # 调试：检查每一条 JSON 能否序列化
# #     for i, t in enumerate(texts):
# #         try:
# #             json.dumps(t, ensure_ascii=False)
# #         except Exception as e:
# #             print(f"[Milvus ERROR] 第 {i} 条 text 无法序列化，原始数据: {repr(t)}")
# #             raise

# #     # 额外数据字段
# #     add_data1s = [{} for _ in chunks]
# #     add_data2s = [{} for _ in chunks]

# #     # 组合成 Milvus 需要的 records 列表
# #     records = [embeddings, pids, chunk_numbers, texts, add_data1s, add_data2s]

# #     try:
# #         collection.insert(records)
# #         print(f"[Milvus] 插入成功，共 {len(chunks)} 条记录")
# #     except Exception as e:
# #         print(f"[Milvus ERROR] 插入失败: {e}")

# # 主处理方法（给Django调用）
# def process_pdf(pdf_path, pid):
#     connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
#     raw_text = extract_and_clean_pdf_text(pdf_path)
#     chunks = split_text(raw_text, max_char_per_chunk=300, overlap=30)
#     insert_into_milvus(chunks, pid)
#     return {"pid": pid, "chunks": len(chunks)}



import fitz  # PyMuPDF
import re
import requests
import json
from pymilvus import connections, Collection, utility
from django.conf import settings
from django.core.cache import cache
import logging
import hashlib
import os
from read_search.embedding_service import EmbeddingService
from read_search.milvus_manager import milvus_manager

# 获取logger
logger = logging.getLogger(__name__)

# ========== 从Django设置中获取配置 ==========
MILVUS_HOST = settings.MILVUS_HOST
MILVUS_PORT = settings.MILVUS_PORT
COLLECTION_NAME = settings.MILVUS_COLLECTION

EMBEDDING_URL = settings.EMBEDDING_URL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
EMBEDDING_DIM = settings.EMBEDDING_DIM

# ========== PDF提取 ==========
def extract_and_clean_pdf_text(pdf_path):
    """
    从PDF文件中提取并清理文本
    
    Args:
        pdf_path (str): PDF文件路径
        
    Returns:
        str: 清理后的文本内容
        
    Raises:
        Exception: PDF文件读取失败时抛出异常
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        
        cleaned_text = re.sub(r'[ \t]+', ' ', full_text)
        logger.info(f"[PDF] 成功提取PDF文本，共 {len(cleaned_text)} 字符")
        return cleaned_text.strip()
    except Exception as e:
        logger.error(f"[PDF ERROR] 提取PDF文本失败: {e}")
        raise

# 注意：文本切块和向量化功能已移至 EmbeddingService
# 为了保持向后兼容性，这里保留原函数作为包装器

def split_text(text, max_char_per_chunk=300, overlap=50):
    """
    文本切块包装器，调用EmbeddingService
    """
    return EmbeddingService.split_text(text, max_char_per_chunk, overlap)

def get_embeddings(texts):
    """
    获取向量包装器，调用EmbeddingService（使用缓存提升性能）
    """
    return EmbeddingService.get_embeddings(texts, use_cache=True)
        
# 清洗 JSON 中可能导致序列化失败的非法字符
# def clean_for_json(val):
#     if isinstance(val, dict):
#         return {k: clean_for_json(v) for k, v in val.items()}
#     elif isinstance(val, list):
#         return [clean_for_json(v) for v in val]
#     elif isinstance(val, str):
#         # 删除 ASCII 控制字符 (0x00-0x1F) 和 DEL (0x7F)
#         val = re.sub(r'[\x00-\x1F\x7F]', '', val)
#         return val
#     else:
#         return str(val)

# ========== 插入 Milvus ==========
def insert_into_milvus(chunks, pid):
    # 使用MilvusManager获取collection
    collection = milvus_manager.get_collection(load=False)

    try:
        collection.delete(f"Pid == {pid}")
        logger.info(f"[Milvus] 删除旧数据，Pid={pid}")
    except Exception as e:
        logger.error(f"[Milvus ERROR] 删除失败: {e}")

    embeddings = EmbeddingService.get_embeddings(chunks, use_cache=True)
    pids = [pid] * len(chunks)
    chunk_numbers = list(range(len(chunks)))
    texts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    add_data1s = [{} for _ in chunks]
    add_data2s = [{} for _ in chunks]

    records = [embeddings, pids, chunk_numbers, texts, add_data1s, add_data2s]

    try:
        collection.insert(records)
        logger.info(f"[Milvus] 插入成功，共 {len(chunks)} 条记录")
    except Exception as e:
        logger.error(f"[Milvus ERROR] 插入失败: {e}")
# def insert_into_milvus(chunks, pid):
#     if not utility.has_collection(COLLECTION_NAME):
#         raise ValueError(f"Collection '{COLLECTION_NAME}' 不存在，请先创建")

#     collection = Collection(COLLECTION_NAME)

#     # 删除旧数据
#     try:
#         collection.delete(f"Pid == {pid}")
#         print(f"[Milvus] 删除旧数据，Pid={pid}")
#     except Exception as e:
#         print(f"[Milvus ERROR] 删除失败: {e}")

#     # 获取向量
#     embeddings = get_embeddings(chunks)

#     pids = [pid] * len(chunks)
#     chunk_numbers = list(range(len(chunks)))

#     # 先构造文本字段
#     texts = [{"content": chunk} for chunk in chunks]
#     texts = [clean_for_json(t) for t in texts]

#     # 调试：检查每一条 JSON 能否序列化
#     for i, t in enumerate(texts):
#         try:
#             json.dumps(t, ensure_ascii=False)
#         except Exception as e:
#             print(f"[Milvus ERROR] 第 {i} 条 text 无法序列化，原始数据: {repr(t)}")
#             raise

#     # 额外数据字段
#     add_data1s = [{} for _ in chunks]
#     add_data2s = [{} for _ in chunks]

#     # 组合成 Milvus 需要的 records 列表
#     records = [embeddings, pids, chunk_numbers, texts, add_data1s, add_data2s]

#     try:
#         collection.insert(records)
#         print(f"[Milvus] 插入成功，共 {len(chunks)} 条记录")
#     except Exception as e:
#         print(f"[Milvus ERROR] 插入失败: {e}")

# 主处理方法（给Django调用）
def get_pdf_hash(pdf_path):
    """
    计算PDF文件的哈希值，用于缓存
    
    Args:
        pdf_path (str): PDF文件路径
        
    Returns:
        str: PDF文件的MD5哈希值
    """
    try:
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except Exception as e:
        logger.error(f"[PDF Hash ERROR] 计算文件哈希失败: {e}")
        return None

def process_pdf(pdf_path, pid, use_cache=True):
    """
    处理PDF文件，提取文本并存储到Milvus
    
    Args:
        pdf_path (str): PDF文件路径
        pid (int): 项目ID
        use_cache (bool): 是否使用缓存
        
    Returns:
        dict: 包含处理结果的字典
        
    Raises:
        Exception: 处理过程中的任何错误
    """
    try:
        logger.info(f"[PDF Processing] 开始处理PDF文件: {pdf_path}, PID: {pid}")
        
        # 检查缓存
        if use_cache:
            pdf_hash = get_pdf_hash(pdf_path)
            if pdf_hash:
                cache_key = f"pdf_processing:{pid}:{pdf_hash}"
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"[PDF Processing] 使用缓存结果: {cached_result}")
                    return cached_result
        
        # 确保Milvus连接
        if not milvus_manager.connect():
            raise ConnectionError("无法连接到Milvus")
        
        # 提取文本
        raw_text = extract_and_clean_pdf_text(pdf_path)
        
        # 文本切块
        chunks = split_text(raw_text, max_char_per_chunk=300, overlap=30)
        
        # 插入Milvus
        insert_into_milvus(chunks, pid)
        
        result = {"pid": pid, "chunks": len(chunks), "status": "success"}
        
        # 缓存结果
        if use_cache and pdf_hash:
            cache_key = f"pdf_processing:{pid}:{pdf_hash}"
            cache.set(cache_key, result, timeout=3600)  # 缓存1小时
            logger.info(f"[PDF Processing] 结果已缓存: {cache_key}")
        
        logger.info(f"[PDF Processing] 处理完成: {result}")
        return result
        
    except Exception as e:
        logger.error(f"[PDF Processing ERROR] 处理失败: {e}")
        return {"pid": pid, "chunks": 0, "status": "failed", "error": str(e)}



