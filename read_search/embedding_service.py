# read_search/embedding_service.py
import re
import requests
import json
from django.conf import settings
from django.core.cache import cache
import logging

# 获取logger
logger = logging.getLogger(__name__)

# 从Django设置中获取向量化模型配置
EMBEDDING_URL = settings.EMBEDDING_URL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
EMBEDDING_DIM = settings.EMBEDDING_DIM

class EmbeddingService:
    """
    统一的向量化服务类，提供文本切块和向量化功能
    """
    
    @staticmethod
    def split_text(text, max_char_per_chunk=300, overlap=50):
        """
        文本切块（优化：按段/句切，每段约200~300字）
        
        Args:
            text (str): 待切块的文本
            max_char_per_chunk (int): 每块最大字符数
            overlap (int): 重叠字符数
            
        Returns:
            list: 切块后的文本列表
        """
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

        # 重叠处理（按字符）
        final_chunks = []
        for i in range(len(chunks)):
            chunk = chunks[i]
            if i > 0 and overlap > 0:
                prev = chunks[i - 1]
                overlap_text = prev[-overlap:] if len(prev) > overlap else prev
                chunk = overlap_text + chunk
            final_chunks.append(chunk)

        logger.info(f"[Chunking] 切分为 {len(final_chunks)} 段，每段约 {max_char_per_chunk} 字")
        return final_chunks
    
    @staticmethod
    def get_embeddings(texts, use_cache=True):
        """
        批量获取向量，支持缓存
        
        Args:
            texts (list): 文本列表
            use_cache (bool): 是否使用缓存
            
        Returns:
            list: 向量列表
        """
        if not texts:
            return []
            
        # 如果使用缓存，先检查缓存
        if use_cache:
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cache_key = f"embedding:{hash(text)}"
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
                    cache_key = f"embedding:{hash(text)}"
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
        """
        从向量化服务获取向量
        
        Args:
            texts (list): 文本列表
            
        Returns:
            list: 向量列表
        """
        try:
            payload = {"model": EMBEDDING_MODEL, "input": texts}
            headers = {"Content-Type": "application/json"}
            response = requests.post(EMBEDDING_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            result = response.json()
            embeddings = result.get("embeddings", [])

            if not embeddings or len(embeddings) != len(texts):
                raise ValueError("返回的 embedding 数量与输入文本数量不匹配")

            for i, emb in enumerate(embeddings):
                if not isinstance(emb, list) or len(emb) != EMBEDDING_DIM:
                    raise ValueError(f"第 {i} 个 embedding 长度错误：{len(emb)}，应为 {EMBEDDING_DIM}")

            logger.info(f"[Embedding] 成功获取 {len(embeddings)} 个向量")
            return embeddings

        except Exception as e:
            logger.error(f"[Embedding ERROR] {e}")
            return [[0.0] * EMBEDDING_DIM for _ in texts]
    
    @staticmethod
    def get_single_embedding(text, use_cache=True):
        """
        获取单个文本的向量
        
        Args:
            text (str): 文本
            use_cache (bool): 是否使用缓存
            
        Returns:
            list: 向量
        """
        embeddings = EmbeddingService.get_embeddings([text], use_cache=use_cache)
        return embeddings[0] if embeddings else [0.0] * EMBEDDING_DIM