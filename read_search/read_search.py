# myapp/read_search.py
import re
import requests
import json
from pymilvus import connections, Collection, utility
from django.conf import settings
from django.core.cache import cache
from .models import TagMatch
from .embedding_service import EmbeddingService
from .milvus_manager import milvus_manager

# 2. 从Django设置中获取配置
MILVUS_HOST = settings.MILVUS_HOST
MILVUS_PORT = settings.MILVUS_PORT
MILVUS_COLLECTION = settings.MILVUS_COLLECTION

# 3. 从Django设置中获取向量化模型配置
EMBEDDING_URL = settings.EMBEDDING_URL
EMBEDDING_MODEL = settings.EMBEDDING_MODEL
EMBEDDING_DIM = settings.EMBEDDING_DIM

# 4. 使用Django ORM查询标签匹配数据
def get_mysql_data(sid):
    """
    根据学生ID获取标签匹配的项目需求ID列表
    
    Args:
        sid (int): 学生ID
        
    Returns:
        list: 包含Sid和Pid的字典列表
    """
    try:
        # 使用Django ORM查询TagMatch模型
        tag_matches = TagMatch.objects.filter(student_id=sid).select_related('student', 'requirement')
        
        # 转换为原有格式以保持兼容性
        return [
            {
                "Sid": tag_match.student.id, 
                "Pid": tag_match.requirement.id
            } 
            for tag_match in tag_matches
        ]
    except Exception as e:
        print(f"查询标签匹配数据时出错: {e}")
        return []

# 注意：文本切块和向量化功能已移至 EmbeddingService
# 为了保持向后兼容性，这里保留原函数作为包装器

def split_text(Query, max_char_per_chunk=300, overlap=50):
    """
    文本切块包装器，调用EmbeddingService
    """
    return EmbeddingService.split_text(Query, max_char_per_chunk, overlap)

def get_embeddings(texts):
    """
    获取向量包装器，调用EmbeddingService（使用缓存提升性能）
    """
    return EmbeddingService.get_embeddings(texts, use_cache=True)

# 6. 从 Milvus 检索
def search_in_milvus(Query, Pids, top_k=5):
    # 使用MilvusManager管理连接
    collection = milvus_manager.get_collection(load=True)
    
    chunks = split_text(Query, max_char_per_chunk=300, overlap=30)
    embeddings = EmbeddingService.get_embeddings(chunks, use_cache=True)
    # 将字符串PID转换为整数，以匹配Milvus中的Int32字段类型
    pid_ints = [int(pid) for pid in Pids]
    expr = f"Pid in {pid_ints}"
    print(f"[DEBUG] 过滤条件: {expr}")
    print(f"[DEBUG] Pids参数: {Pids} -> {pid_ints}")
    print(f"[DEBUG] 嵌入向量数量: {len(embeddings)}")
    #query_vector = model.encode(embeddings).tolist()
    # 使用所有嵌入向量进行搜索
    if not embeddings:
        embeddings = [[0.0] * EMBEDDING_DIM]
        print(f"[DEBUG] 使用默认嵌入向量")
    
    results = collection.search(
        data=embeddings,
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"nprobe": 10}},
        limit=top_k,
        expr=expr,  # 这里添加过滤条件
        output_fields=["chunk_number", "text"]
    )
    # 合并所有搜索结果
    print(f"[DEBUG] Milvus搜索返回 {len(results)} 个结果集")
    output = []
    seen_ids = set()  # 用于去重
    
    for i, result_set in enumerate(results):
        print(f"[DEBUG] 结果集 {i} 包含 {len(result_set)} 个结果")
        for hit in result_set:
            hit_id = hit.entity.get("chunk_number")
            content = hit.entity.get("text")
            score = hit.score
            print(f"[DEBUG] 找到结果: id={hit_id}, content_len={len(content) if content else 0}, score={score}")
            
            # 避免重复结果
            if hit_id not in seen_ids:
                seen_ids.add(hit_id)
                output.append({
                    "id_chunk": hit_id,  # 将原来的 id 字段改为 id_chunk
                    "content": content,
                    "score": score
                })
    
    print(f"[DEBUG] 最终输出 {len(output)} 个结果")
    # 按分数降序排序并限制结果数量
    output.sort(key=lambda x: x["score"], reverse=True)
    return output[:top_k]