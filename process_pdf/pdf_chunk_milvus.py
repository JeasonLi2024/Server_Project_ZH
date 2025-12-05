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



