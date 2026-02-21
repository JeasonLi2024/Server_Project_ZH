# 进阶推荐系统设计方案：双路召回与动态画像

## 1. 概述 (Overview)

本文档基于《智慧协同平台 - 需求推荐系统与性能优化技术方案》及最新的“方案B”缓存策略，详细阐述针对**向量检索 (Vector Retrieval)** 和 **动态用户画像 (Dynamic User Profiling)** 的最佳搭配实践方案。

本方案旨在通过引入**双路召回 (Dual-Path Retrieval)** 架构，将传统的基于规则的静态画像匹配（Symbolic Matching）与基于语义的向量检索（Semantic Matching）相结合，利用用户实时行为构建动态画像，从而显著提升推荐系统的准确性、多样性和时效性。

---

## 2. 核心架构设计：双路召回 (Dual-Path Architecture)

我们采用业界成熟的 **"召回 (Retrieval) -> 粗排 (Rough Ranking) -> 精排 (Re-ranking)"** 漏斗模型。但在本项目规模下，我们将粗排与精排合并为一步“双路合并与打分 (Merger & Scoring)”。

### 2.1 整体流程图

```mermaid
graph TD
    User[用户请求] --> Profile[构建/获取用户画像]
    Profile --> PathA[A路: 语义向量召回]
    Profile --> PathB[B路: 规则标签召回]
    
    subgraph "动态画像构建 (Dynamic Profiling)"
        History[最近浏览历史] --> VectorCalc[实时向量计算]
        Behavior[行为反馈] --> TagWeight[动态标签加权]
        VectorCalc --> UserVector[用户查询向量]
        TagWeight --> UserTags[加权标签集合]
    end
    
    UserVector --> PathA
    UserTags --> PathB
    
    PathA -->|Top 200 (Sim Score)| Merger[双路合并 & 归一化]
    PathB -->|Top 200 (Static Score)| Merger
    
    Merger --> Dedupe[去重过滤 (Bloom Filter / Set)]
    Dedupe --> Cache[写入候选集缓存 (TTL 10min)]
    
    Cache --> Filter[业务筛选 (Budget/Time/Status)]
    Filter --> Pagination[分页返回]
```

---

## 3. 动态用户画像最佳实践 (Dynamic User Profiling)

动态画像分为**向量侧**和**标签侧**两部分，分别服务于 A 路和 B 路召回。

### 3.1 向量侧：实时行为向量 (Real-time Behavior Vector)
**目标**：捕捉用户当前的瞬时兴趣（Short-term Interest）。
**逻辑**：
1.  **输入**：从 `UserHistoryService` 获取用户最近浏览的 **N=5** 个需求 ID。
2.  **计算**：
    - 从 Milvus 批量拉取这 5 个需求的向量。
    - 计算平均向量 `Avg_Vector`。
    - 获取用户静态画像（技能+兴趣标签文本）生成的 `Static_Vector`。
    - **融合公式**：`User_Query_Vector = α * Static_Vector + (1-α) * Avg_Vector`
    - 建议 `α = 0.3`，即 70% 权重给予最近行为，30% 给予长期画像，确保推荐内容随用户点击实时变化。
3.  **缓存**：计算出的 `User_Query_Vector` 存入 Redis，TTL 设为 **10分钟**。避免每次请求都重新计算。

### 3.2 标签侧：动态权重标签 (Dynamic Weighted Tags)
**目标**：修正静态标签的权重，发现用户未显式设置但感兴趣的领域。
**逻辑**：
1.  **存储**：使用 Redis Hash 结构 `user:dynamic_tags:{user_id}`。
    - Field: `tag_id`
    - Value: `score` (累积热度)
2.  **更新机制 (异步)**：
    - 用户点击需求：该需求关联的 `tag1` (领域) +1 分，`tag2` (技能) +0.5 分。
    - 用户收藏需求：+3 分。
    - 用户申请项目：+5 分。
3.  **衰减机制**：
    - 每次更新时，将旧分数乘以衰减因子（如 0.95），或者设置 Redis Key 的整体过期时间（如 3 天）。
4.  **应用**：
    - 在 B 路召回时，不仅匹配用户静态标签，还匹配动态权重 Top 3 的标签。
    - 静态匹配分计算时，若命中动态高分标签，额外加权（例如 `Score * (1 + Dynamic_Score * 0.1)`）。

---

## 4. 双路召回详细设计 (Dual-Path Retrieval)

### 4.1 A路：语义向量召回 (Semantic Path)
- **工具**：Milvus Vector Database。
- **输入**：`User_Query_Vector` (1536维)。
- **过程**：
  - 执行 ANN (Approximate Nearest Neighbor) 搜索。
  - `limit=200` (召回 Top 200)。
  - `metric_type="COSINE"` (余弦相似度)。
- **输出**：`[(req_id, similarity_score), ...]`，其中 score 范围通常在 0.0 ~ 1.0。

### 4.2 B路：规则画像召回 (Symbolic Path)
- **工具**：MySQL / Django ORM。
- **输入**：用户静态标签 + 动态高分标签。
- **过程**：
  - `Requirement.objects.filter(tag1__in=tags | tag2__in=tags)`
  - 使用 `annotate` 计算静态分（技能匹配、兴趣匹配、新鲜度）。
  - 按分数降序取 Top 200。
- **输出**：`[(req_id, static_score), ...]`，其中 score 范围通常在 0 ~ 100+。

---

## 5. 双路合并与打分 (Merger & Scoring)

**核心挑战**：如何将 A 路的相似度（0~1）与 B 路的规则分（0~100）统一？

### 5.1 归一化与加权公式
$$ Final\_Score = (Static\_Score) + (Vector\_Score \times W_{vec}) + (Hot\_Score) $$

- **Static_Score**: B 路召回的原始分数。
- **Vector_Score**: A 路召回的相似度 (Cosine Similarity)。
- **$W_{vec}$ (向量权重系数)**: 建议设为 **50**。
  - 意味着：如果一个需求与用户意图完全匹配（Sim=1.0），它将获得 50 分，相当于命中 5 个技能标签（10分/个）。
- **Hot_Score**: `log10(views + 1) * 2`。

### 5.2 合并逻辑
1.  **并集**：取 A 路与 B 路 ID 的并集（Max 400 个）。
2.  **补全**：
    - 对于仅在 A 路出现的需求，需查询其静态属性（Tags, Created_at）计算 Static_Score。
    - 对于仅在 B 路出现的需求，其 Vector_Score 视为 0（或设为一个小阈值）。
3.  **排序**：按 `Final_Score` 降序排列。
4.  **截断**：取 Top 300 作为最终候选集。

---

## 6. 性能优化与缓存策略 (Performance & Caching)

为了在引入向量计算后仍保持 <200ms 的响应速度，必须采用多级缓存和异步处理。

### 6.1 是否需要双路缓存？ (Dual-Layer Caching)
**结论：是，必须采用双层缓存架构。**

*   **L1: 用户画像缓存 (User Profile Cache)**
    *   **内容**：`User_Query_Vector`。
    *   **TTL**：**5~10 分钟**。
    *   **理由**：向量计算（Milvus Fetch + Average）和生成（Embedding API）耗时较长（50ms+）。用户的短期兴趣在几分钟内不会剧烈突变，复用向量可大幅降低延迟。
*   **L2: 候选集缓存 (Candidate Cache) - 方案B核心**
    *   **内容**：合并、排序、去重后的 **ID 列表** (`List[int]`)。
    *   **Key**：`recommend_candidates_{user_id}`。
    *   **TTL**：**10 分钟**。
    *   **理由**：这是推荐结果的“快照”。前端的分页（Page 2, 3...）和筛选（Budget, Status...）都直接基于此缓存进行内存过滤，速度极快（<10ms）。

### 6.2 是否需要异步任务？ (Async Tasks)
**结论：是，用于写操作和重计算。**

*   **场景 1：动态标签更新 (Update Dynamic Tags)**
    *   **机制**：用户点击/收藏时，不阻塞 API，而是发送 Celery 任务 `update_user_dynamic_profile_task`。
    *   **操作**：更新 Redis Hash 中的标签权重。
*   **场景 2：向量索引维护 (Vector Indexing)**
    *   **机制**：需求发布/修改时，保持现有的 Signal -> Celery 流程。
    *   **操作**：调用 Embedding API 并写入 Milvus。
*   **场景 3 (可选)：缓存预热 (Cache Warming)**
    *   **机制**：每天凌晨或用户首次登录时，触发 Celery 任务预先计算并缓存 `User_Query_Vector`。

---

## 7. 异常处理与降级 (Failover)

引入外部系统（Milvus, Embedding API）增加了故障风险，必须设计降级策略。

1.  **Milvus 超时/不可用**：
    - 设置严格超时时间（如 200ms）。
    - 捕获异常，**自动降级为仅 B 路（规则召回）**。
    - 用户感知：推荐结果依然存在，只是精准度略降（缺少了语义相关性推荐）。
2.  **Embedding API 限流/失败**：
    - 无法生成新向量时，使用上次缓存的 `User_Query_Vector`。
    - 若无缓存，降级为使用用户静态标签 ID 进行 B 路召回。

---

## 8. 总结

本方案通过 **"L1 画像缓存 + L2 结果缓存"** 的双层缓存体系解决性能问题，通过 **"语义 + 规则"** 的双路召回解决推荐质量问题，并利用 **"异步任务"** 处理高频的动态画像更新，是一套兼顾效果与性能的生产级解决方案。
