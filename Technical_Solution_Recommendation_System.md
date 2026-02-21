# 智慧协同平台 - 需求推荐系统与性能优化技术方案

## 1. 概述
本文档详细记录了智慧协同平台（Server_Project_ZH）针对需求列表页（Requirements List）进行的推荐系统设计、用户体验增强及生产级性能优化方案。该方案旨在在不引入额外推荐引擎组件（如 ElasticSearch 或独立 AI 服务）的前提下，基于 Django ORM、Redis 和 MySQL 实现一套高效、实时且具备冷启动处理能力的推荐系统。

## 2. 核心功能模块

### 2.1 智能推荐排序 (Smart Recommendation)
针对学生用户（Student），系统提供基于用户画像的个性化推荐排序（`sort_type='recommend'`）。

#### 2.1.1 评分模型
采用**混合加权评分模型**，在数据库层面通过 `annotate` 动态计算每个需求的总分（Total Score），公式如下：

$$ Total Score = Skill Score + Interest Score + Freshness Score + Hot Score $$

- **技能匹配分 (Skill Score)**:
  - 逻辑：需求的能力标签 (`tag2`) 命中用户的技能标签。
  - 权重：每命中一个标签 **+10分**。
  - 目的：确保推荐的需求符合学生的能力栈。

- **兴趣匹配分 (Interest Score)**:
  - 逻辑：需求的领域标签 (`tag1`) 命中用户的兴趣标签。
  - 权重：每命中一个标签 **+5分**。
  - 目的：推荐学生感兴趣的领域。

- **新鲜度分 (Freshness Score)**:
  - 逻辑：基于需求发布时间 (`created_at`)。
  - 权重：
    - 3天内发布：**+20分**
    - 7天内发布：**+10分**
    - 超过7天：0分
  - 目的：防止老旧需求霸榜，保证列表的流动性。

- **热度分 (Hot Score)**:
  - 逻辑：基于浏览量 (`views`) 的对数平滑处理。
  - 公式：$ \log_{10}(\text{views} + 1) \times 2 $
  - 目的：利用群体智慧，适当推荐热门内容，同时避免马太效应过强。

#### 2.1.2 推荐理由外显
为了增强用户信任感，接口会在返回数据中明确告知推荐理由 (`recommendation_reason`)：
- **"技能匹配"**: 命中 `tag2`。
- **"兴趣匹配"**: 命中 `tag1`。
- **"近期发布"**: 发布时间在 7 天内。
- **"热门需求"**: 浏览量 > 9 (热度分 > 2)。

### 2.2 浏览量高并发优化 (High Concurrency Views)
针对需求浏览量这一高频写操作，采用 **Redis 缓冲 + 异步持久化 + 读时合并** 的架构，彻底解决数据库行锁瓶颈。

#### 2.2.1 架构流程
1.  **写缓冲 (Write Buffer)**:
    - 用户访问详情页时，不直接更新 MySQL。
    - 使用 `cache.incr` 将浏览量增量写入 Redis Key: `requirement_views_buffer_{id}`。
    - 操作耗时从 ~10ms (DB Update) 降至 ~0.5ms (Redis Incr)。

2.  **读时合并 (Read-time Merge)**:
    - **详情页**: 读取 MySQL `views` + Redis `buffer`，返回总和。
    - **列表页**: 批量获取当前页所有需求的 Redis `buffer`，在内存中叠加到 `views` 字段。
    - **优势**: 用户看到的浏览量永远是实时的，没有任何延迟。

3.  **异步持久化 (Async Persistence)**:
    - 利用 Celery 定时任务 (`sync_requirement_views_to_db`)。
    - **频率**: 每 5 分钟执行一次。
    - **逻辑**: 扫描 Redis buffer keys -> 批量更新 MySQL (`F('views') + buffer`) -> 清除 Redis buffer。
    - **安全性**: 使用原子递减或 GetSet 策略防止数据丢失。

### 2.3 冷启动处理 (Cold Start)
针对新用户和新需求，设计了专门的降级策略。

#### 2.3.1 用户冷启动 (User Cold Start)
- **场景**: 用户刚注册，未设置兴趣或技能标签。
- **策略**: **热度 + 新鲜度混合排序**。
  - 放弃技能/兴趣匹配分。
  - 调整新鲜度权重：3天内 **+50分**（大幅提升新需求曝光）。
  - 调整热度权重：`log10(views+1) * 5`。
- **目的**: 即使没有画像，也能看到高质量（热门）和活跃（最新）的内容。

#### 2.3.2 物品冷启动 (Item Cold Start)
- **场景**: 新发布的需求，浏览量为 0。
- **策略**: 依靠**新鲜度加分**机制。
  - 新需求自带 **+20分** (常规) 或 **+50分** (冷启动模式) 的初始分。
  - 这足以让其排在浏览量较高但发布已久的老需求前面，获得初始曝光流量。

### 2.4 浏览历史接口 (Viewing History API)

新增用户浏览足迹接口，记录并展示用户的浏览历史，支持需求（Requirement）和项目（Project）两种类型的浏览记录。

#### 2.4.1 接口定义
- **URL**: `GET /api/v1/user/history/`
- **Method**: `GET`
- **Permission**: `IsAuthenticated` (仅登录用户可用)
- **Params**:
  - `page`: 页码 (int, default: 1)
  - `page_size`: 每页数量 (int, default: 20)
  - `type`: 浏览类型 (string, enum: `requirement`, `project`, default: `requirement`)
- **Response Example**:
  ```json
  {
    "code": 200,
    "message": "获取浏览历史成功",
    "data": {
      "results": [
        {
          "id": 101,
          "title": "基于深度学习的图像识别系统",
          "status": "published",
          // ... 其他需求/项目详情字段 ...
        },
        ...
      ],
      "pagination": {
        "current_page": 1,
        "total_pages": 5,
        "total_count": 89,
        "page_size": 20,
        "previous_url": null,
        "next_url": "http://example.com/api/v1/user/history/?page=2"
      }
    }
  }
  ```

#### 2.4.2 技术实现 (Technical Implementation)
本功能完全基于 **Redis Sorted Set (ZSet)** 实现，以保证高性能读写和天然的时间排序特性。

1.  **存储结构**:
    - **Key**: `user:view_history:{type}:{user_id}` (例如 `user:view_history:requirement:1001`)
    - **Member**: `item_id` (需求ID或项目ID)
    - **Score**: `timestamp` (Unix 时间戳，精确到秒)

2.  **核心逻辑**:
    - **记录 (Record)**:
      - 触发时机：用户调用 `get_requirement` (或 `get_project`) 详情接口时。
      - 操作：`ZADD key timestamp item_id`。如果记录已存在，更新其 Score 为最新时间。
      - 维护：每次写入后调用 `ZREMRANGEBYRANK`，仅保留最新的 **1000** 条记录，防止无限增长。
      - 过期：设置 Key 的 TTL 为 **90天**，长期未活跃的数据自动清理。
    - **查询 (Query)**:
      - 操作：`ZREVRANGE key start end` 按 Score 倒序获取 ID 列表。
      - 详情：根据 ID 列表批量从 MySQL 查询详情对象，并按 Redis 中的顺序重排。

3.  **代码位置**:
    - **Service**: `user/services.py` -> `UserHistoryService` (封装 Redis 操作)
    - **View**: `user/views.py` -> `get_view_history` (API 接口)
    - **URL**: `user/urls.py` -> `path('history/', ...)`

#### 2.4.3 推荐系统集成 (Integration)
浏览历史不仅用于展示，还用于优化推荐系统的体验。
- **自动去重**: 在 `project/views.py` 的 `list_requirements` 接口中，系统会获取用户的浏览历史 ID 集合，并在推荐列表中排除这些已读内容（除非用户显式请求查看历史），确保用户每次刷新推荐列表都能看到新鲜内容。

## 3. 性能优化方案

### 3.1 数据库索引优化
在 `project/models.py` 中针对 `Requirement` 表建立了精细的索引策略：

- **单字段索引**: `status`, `organization`, `created_at`, `views` 等，覆盖基础过滤。
- **复合索引 (Composite Indexes)**:
  - `['status', 'created_at']`: 覆盖 "查询已发布需求并按时间排序" 的最高频场景。
  - `['organization', 'status']`: 优化组织管理后台查询。
  - `['status', 'organization', 'created_at']`: 覆盖最长前缀匹配。
- **排序索引**: `['-views']`, `['-created_at']`，避免数据库进行 Filesort。

### 3.2 缓存策略
在 `project/views.py` 中实现了多级缓存：

- **推荐结果缓存**:
  - **Key**: `recommend_list_{user_id}_{page}_{page_size}`
  - **TTL**: 5分钟。
  - **内容**: 存储计算昂贵的推荐排序结果列表。
  - **逻辑**: 命中缓存后，依然执行**读时合并**，更新浏览量数据，确保 "推荐列表结构不变，但数据实时"。

## 4. 进阶优化技术方案 (Advanced Optimization)

本章节基于现有基础架构，提出针对“去重”、“语义匹配”和“动态画像”的进阶优化方案。该方案复用现有的 `project/services.py` 基础设施。

### 4.1 浏览历史与去重 (Viewing History & Deduplication)

#### 4.1.1 存储设计
采用 **Redis Sorted Set (ZSet)** 兼顾业务展示与去重过滤。
- **Key**: `user:view_history:{user_id}`
- **Member**: `req_id` (需求ID)
- **Score**: `timestamp` (浏览时间戳)
- **TTL**: 90天 (自动过期)

#### 4.1.2 核心流程
1.  **写入 (Write)**:
    - 用户访问详情页时执行 `ZADD`。
    - 每次写入后调用 `ZREMRANGEBYRANK` 保留最新的 1000 条记录，控制内存。
2.  **业务查询 (Read)**:
    - “我的足迹”接口使用 `ZREVRANGE` 分页获取。
3.  **推荐去重 (Filter)**:
    - 推荐接口 (`list_requirements`) 先拉取全量历史 ID (`ZRANGE 0 -1`)。
    - 在内存中过滤掉已读需求，确保推荐内容的新鲜感。

### 4.2 向量检索与语义推荐 (Vector Search)

#### 4.2.1 架构复用
- **Collection**: `project_embeddings` (已在 `project/services.py` 中定义)。
- **Model**: `text-embedding-v4` (Dim=1536)。
- **Service**: 复用 `EmbeddingService`。

#### 4.2.2 向量化策略
- **需求侧 (Item)**:
  - 触发：需求发布/更新 (`post_save` signal)。
  - 内容：`Title + Brief + Description + Tags`。
  - 存储：调用 `sync_requirement_vectors` 存入 Milvus。
- **用户侧 (User)**:
  - **实时 Query 生成**: 不存储静态用户向量，而是基于当前画像实时生成。
  - **内容组合**:
    ```python
    text = f"User Interests: {interest_tags_str}\nUser Skills: {skill_tags_str}"
    # 可选：加入最近的高权重动态标签
    ```
  - **语言支持**: 模型支持中英文混合，无需特殊处理。

#### 4.2.3 混合检索流程
在 `list_requirements` 中增加一路召回：
1.  **向量召回**: 使用用户 Query Vector 在 Milvus 中搜索 Top 50 相似需求。
2.  **去重**: 利用 Milvus 标量过滤 (`expr="id not in {viewed_ids}"`) 或内存过滤。
3.  **加权融合**:
    - `Total Score += (Semantic Similarity * 100)`
    - 使得标签未完全命中但语义相关的需求也能上榜。

### 4.3 动态用户画像 (Dynamic User Profile)

#### 4.3.1 设计思路
基于 **Redis Hash** 捕捉用户实时行为，赋予标签临时权重。

- **Key**: `user:dynamic_profile:{user_id}`
- **Field**: `tag_id`
- **Value**: `weight` (累积权重)
- **TTL**: 7天 (短期兴趣自动消退)

#### 4.3.2 行为反馈权重
- **点击**: +1
- **收藏**: +5
- **申请**: +10
- **取消收藏**: -5

#### 4.3.3 应用逻辑
推荐计算时，标签得分不再是固定的 10 分/个，而是：
`Score = Base_Score * (1 + Dynamic_Weight * 0.1)`
这能让用户最近关注领域的权重迅速提升。

### 4.4 性能影响与优化策略 (Performance & Optimization)

引入向量检索和动态画像后，接口响应时间必然增加。为保证用户体验（目标响应 < 200ms），必须采取以下优化措施：

#### 4.4.1 并行执行 (Parallel Execution)
推荐接口涉及多路召回（MySQL 规则召回 + Milvus 向量召回）。
- **策略**: 使用 `concurrent.futures.ThreadPoolExecutor` 并行执行：
  1.  查询 MySQL 获取基于标签的候选集。
  2.  调用 Embedding 服务生成 Query Vector 并查询 Milvus。
  3.  从 Redis 获取动态画像权重。
- **效果**: 接口总耗时取决于最慢的一路，而非累加。

#### 4.4.2 缓存策略 (Caching Strategy)
- **Query Vector 缓存**: 用户标签不会频繁变化，生成的 Query Vector 可缓存 10~30 分钟，避免每次请求都调用模型服务。
- **推荐结果缓存**: 现有的 5 分钟列表缓存机制依然有效，能抵消大部分计算开销。

#### 4.4.3 快速降级 (Fail-fast)
- **超时控制**: 对 Embedding 和 Milvus 调用设置严格超时（如 150ms）。
- **降级逻辑**: 若外部服务超时或不可用，立即降级为仅使用 MySQL 规则推荐，确保接口高可用。

#### 4.4.4 数据结构约束
- **浏览历史**: 严格限制 Redis ZSet 长度（Max 1000），防止大 Key 阻塞 Redis。

## 5. 运维监控

### 5.1 关键指标
- **接口延迟**: P95/P99 响应时间。
- **Redis 内存**: 关注 `user:view_history:*` 和 `user:dynamic_profile:*` 的内存占用。
- **Milvus 状态**: 连接数、查询延迟。
- **Embedding 服务**: 调用成功率、平均耗时。

### 5.2 日志监控
- 关注 `WARNING` 级别的降级日志（如 "Milvus timeout, fallback to rule-based recommendation"）。
