import fitz  # PyMuPDF
import re
import requests
import json
from pymilvus import connections, Collection, utility

# ========== 配置 ==========
MILVUS_HOST = "100.116.251.123"
MILVUS_PORT = "19530"
COLLECTION_NAME = "enterprise_vectors"

EMBEDDING_URL = "http://100.116.251.123:11434/api/embed"  
EMBEDDING_MODEL = "bge-m3:567m"
EMBEDDING_DIM = 1024

# ========== PDF提取 ==========
def extract_and_clean_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()

    cleaned_text = re.sub(r'[ \t]+', ' ', full_text)
    return cleaned_text.strip()

# 文本切块（优化：按段/句切，每段约200~300字）
def split_text(text, max_char_per_chunk=300, overlap=50):
    sentences = re.split(r'[\n\u3002\uff1f\uff01]', text)  
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

        return embeddings

    except Exception as e:
        print(f"[Embedding ERROR] {e}")
        return [[0.0] * EMBEDDING_DIM for _ in texts]
        
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
    if not utility.has_collection(COLLECTION_NAME):
        raise ValueError(f"Collection '{COLLECTION_NAME}' 不存在，请先创建")

    collection = Collection(COLLECTION_NAME)

    try:
        collection.delete(f"Pid == {pid}")
        print(f"[Milvus] 删除旧数据，Pid={pid}")
    except Exception as e:
        print(f"[Milvus ERROR] 删除失败: {e}")

    embeddings = get_embeddings(chunks)
    pids = [pid] * len(chunks)
    chunk_numbers = list(range(len(chunks)))
    texts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    add_data1s = [{} for _ in chunks]
    add_data2s = [{} for _ in chunks]

    records = [embeddings, pids, chunk_numbers, texts, add_data1s, add_data2s]

    try:
        collection.insert(records)
        print(f"[Milvus] 插入成功，共 {len(chunks)} 条记录")
    except Exception as e:
        print(f"[Milvus ERROR] 插入失败: {e}")
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
def process_pdf(pdf_path, pid):
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    raw_text = extract_and_clean_pdf_text(pdf_path)
    chunks = split_text(raw_text, max_char_per_chunk=300, overlap=30)
    insert_into_milvus(chunks, pid)
    return {"pid": pid, "chunks": len(chunks)}



