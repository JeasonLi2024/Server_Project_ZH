# myapp/read_search.py
import pymysql
import re
from pymilvus import connections, Collection, utility
import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# 文本切块（优化：按段/句切，每段约200~300字）
def split_text(Query, max_char_per_chunk=300, overlap=50):
    sentences = re.split(r'[\n\u3002\uff1f\uff01]', Query)  
    chunks = []
    current = ""

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) <= max_char_per_chunk:
            current += sent + "\u3002"  #加个句号
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

    print(f"[Chunking] 切分为 {len(final_chunks)} 段，每段约 {max_char_per_chunk} 字")
    return final_chunks

# 批量获取向量
def get_embeddings(texts):
    """
    获取文本的向量表示
    """
    try:
        payload = {"model": settings.EMBEDDING_MODEL, "input": texts}
        headers = {"Content-Type": "application/json"}
        response = requests.post(settings.EMBEDDING_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()
        embeddings = result.get("embeddings", [])

        if not embeddings or len(embeddings) != len(texts):
            raise ValueError("返回的 embedding 数量与输入文本数量不匹配")

        for i, emb in enumerate(embeddings):
            if not isinstance(emb, list) or len(emb) != settings.EMBEDDING_DIM:
                raise ValueError(f"第 {i} 个 embedding 长度错误：{len(emb)}，应为 {settings.EMBEDDING_DIM}")

        logger.info(f"成功获取 {len(texts)} 个文本的向量表示")
        return embeddings

    except Exception as e:
        logger.error(f"获取向量表示失败: {e}")
        return [[0.0] * settings.EMBEDDING_DIM for _ in texts]

# 6. 从 Milvus 检索 (已弃用，请使用 milvus_cache_service.py 中的缓存版本)
def search_in_milvus(Pids, top_k=5):
    """
    原始的 Milvus 检索函数，已被新的连接管理器版本替代。
    保留此函数仅为向后兼容，建议使用 read_search.py 中的统一版本。
    """
    logger.warning("使用了已弃用的 search_in_milvus 函数，建议使用 milvus_cache_service.py 中的缓存版本")
    
    try:
        # 使用 Django settings 中的配置
        connections.connect(
            alias="default", 
            host=settings.MILVUS_HOST, 
            port=settings.MILVUS_PORT
        )
        collection = Collection(settings.MILVUS_COLLECTION)
        collection.load()
        
        results = collection.query(
            expr=f"Pid=={Pids}",
            limit=top_k,
            output_fields=["Pid", "chunk_number", "text"]
        )
        
        output = []
        for hit in results:
            output.append({
                "id": hit.get("Pid"),
                "id_chunk": hit.get("chunk_number"),
                "content": hit.get("text")
            })
        
        logger.info(f"从 Milvus 检索到 {len(output)} 条记录，Pid: {Pids}")
        return output
        
    except Exception as e:
        logger.error(f"Milvus 检索失败: {e}")
        return []
    finally:
        try:
            connections.disconnect("default")
        except:
            pass
