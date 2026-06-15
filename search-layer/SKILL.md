---
name: search-layer
description: >
  DEFAULT search tool for ALL search/lookup needs. Multi-source search and deduplication
  layer with intent-aware scoring. Integrates Brave Search (web_search), Exa, Tavily,
  and Grok to provide high-coverage, high-quality results. Automatically classifies
  query intent and adjusts search strategy, scoring weights, and result synthesis.
  Use for ANY query that requires web search — factual lookups, research, news,
  comparisons, resource finding, "what is X", status checks, etc. Do NOT use raw
  web_search directly; always route through this skill.
---

# Search Layer v2.3 — 意图感知多源检索协议

五源协同：Brave (`web_search`) + Exa + Tavily + Grok + Firecrawl。按意图自动选策略、调权重、做合成。

## 执行流程

```
用户查询
    ↓
[Phase 1] 意图分类 → 确定搜索策略
    ↓
[Phase 2] 查询分解 & 扩展 → 生成子查询
    ↓
[Phase 3] 多源并行检索 → Brave + search.py (Exa + Tavily + Grok + Firecrawl)
    ↓
[Phase 4] 结果合并 & 排序 → 去重 + 意图加权评分
    ↓
[Phase 5] 知识合成 → 结构化输出
```

---

## Phase 1: 意图分类

收到搜索请求后，**先判断意图类型**，再决定搜索策略。不要问用户用哪种模式。

| 意图 | 识别信号 | Mode | Freshness | 权重偏向 |
|------|---------|------|-----------|---------|
| **Factual** | "什么是 X"、"X 的定义"、"What is X" | answer | — | 权威 0.5 |
| **Status** | "X 最新进展"、"X 现状"、"latest X" | deep | pw/pm | 新鲜度 0.5 |
| **Comparison** | "X vs Y"、"X 和 Y 区别" | deep | py | 关键词 0.4 + 权威 0.4 |
| **Tutorial** | "怎么做 X"、"X 教程"、"how to X" | answer | py | 权威 0.5 |
| **Exploratory** | "深入了解 X"、"X 生态"、"about X" | deep | — | 权威 0.5 |
| **News** | "X 新闻"、"本周 X"、"X this week" | deep | pd/pw | 新鲜度 0.6 |
| **Resource** | "X 官网"、"X GitHub"、"X 文档" | fast | — | 关键词 0.5 |

> 详细分类指南见 `references/intent-guide.md`

**判断规则**：
1. 扫描查询中的信号词
2. 多个类型匹配时选最具体的
3. 无法判断时默认 `exploratory`

---

## Phase 2: 查询分解 & 扩展

根据意图类型，将用户查询扩展为一组子查询：

### 通用规则
- **技术同义词自动扩展**：k8s→Kubernetes, JS→JavaScript, Go→Golang, Postgres→PostgreSQL
- **中文技术查询**：同时生成英文变体（如 "Rust 异步编程" → 额外搜 "Rust async programming"）

### 按意图扩展

| 意图 | 扩展策略 | 示例 |
|------|---------|------|
| Factual | 加 "definition"、"explained" | "WebTransport" → "WebTransport", "WebTransport explained overview" |
| Status | 加年份、"latest"、"update" | "Deno 进展" → "Deno 2.0 latest 2026", "Deno update release" |
| Comparison | 拆成 3 个子查询 | "Bun vs Deno" → "Bun vs Deno", "Bun advantages", "Deno advantages" |
| Tutorial | 加 "tutorial"、"guide"、"step by step" | "Rust CLI" → "Rust CLI tutorial", "Rust CLI guide step by step" |
| Exploratory | 拆成 2-3 个角度 | "RISC-V" → "RISC-V overview", "RISC-V ecosystem", "RISC-V use cases" |
| News | 加 "news"、"announcement"、日期 | "AI 新闻" → "AI news this week 2026", "AI announcement latest" |
| Resource | 加具体资源类型 | "Anthropic MCP" → "Anthropic MCP official documentation" |

### 场景动作：trade_data_intelligence（海关数据与贸易数据层）

当查询属于外贸调研、客户开发、竞品分析、供应商/企业背调、进口商/经销商识别、目标国市场进入、判断企业真实出口能力等场景时，启用 `trade_data_intelligence` 场景动作。

**重要：`trade_data_intelligence` 不是 `search.py --intent` 参数。** `search.py --intent` 仍只能使用 `factual / status / news / comparison / tutorial / exploratory / resource`。不要把 `trade_data_intelligence` 传给脚本。

#### 检索目标

- 海关数据、进出口记录、提单/航运记录摘要
- 目标国进口商、经销商、采购商名录
- HS Code、交易频次、出货量、金额、贸易流向
- 竞品供应商的客户线索
- B2B 平台成交/询盘/供应商交易线索
- 用户提供的已购海关数据文件中的客户筛选与采购规律

#### 查询模板

```text
"[Company English Name]" import export records
"[Company English Name]" customs data
"[Company English Name]" bill of lading
"[Brand]" shipment records
"[Product English Name]" "[Country]" importers
"[HS Code]" "[Country]" importers distributors
"[Competitor]" customer import records
"[Company English Name]" Alibaba transaction supplier
"[Company English Name]" Made-in-China export supplier
"[中文公司名]" 海关数据
"[中文公司名]" 出口 进口商
"[中文公司名]" 提单
```

#### 输出要求

- 贸易/海关线索不要并入普通 authority 排序；单独作为 `trade_data_leads` 处理。
- 报告中必须区分：`已获取记录 / 公开线索 / 用户数据待导入 / 缺失待验证`。
- 如果没有查到，必须输出“海关数据缺失/待验证”，并说明对客户开发、竞品判断或供应商评估的影响。
- 不绕过登录墙、付费墙、验证码或权限限制；付费数据库和用户私有数据必须由用户授权或提供。

---
### 场景动作：social_intelligence（公开社媒与职业网络情报层）

当查询属于外贸调研、客户开发、竞品分析、企业背调、海外渠道识别、经销商/代理商查找、品牌口碑/投诉/风险、展会前背调、关键人员/岗位识别、判断企业是否真实做出口等场景时，启用 `social_intelligence` 场景动作。

**重要：`social_intelligence` 不是 `search.py --intent` 参数。** `search.py --intent` 仍只能使用 `factual / status / news / comparison / tutorial / exploratory / resource`。不要把 `social_intelligence` 传给脚本，否则会报错。

#### 平台分级与工具优先级

- **高价值优先**：LinkedIn、官网关联社媒、Facebook、YouTube。
- **实时/讨论补充**：X / Twitter，最高优先级默认直接用 `grok_search model="grok-4.3" platform="Twitter"`；如遇 403/503/超时等错误，间隔约 2 秒重试 2 次（合计最多 3 次请求）；仅在 Grok 仍失败后，再用 `site:x.com` / `site:twitter.com`、Tavily、dual_search 作补充；不要使用已废弃的 Exa `tweet` category。
- **尽力检索**：Instagram、TikTok、微信公众号、抖音、视频号、小红书。
- **口碑补充**：Reddit、Quora、行业论坛、专业社区。

#### 硬前置：实体消歧

社媒检索前先确认公司英文名、品牌名、官网域名、产品英文标准名；中文企业还要覆盖中文全称、简称、拼音名、B2B 店铺名。非英语目标市场追加本地语言关键词（如 distribuidor / fornecedor / موزع / дистрибьютор 等）。

#### 查询模板

企业调研：
```text
"[Company English Name]" LinkedIn
site:linkedin.com/company "[Company English Name]"
site:linkedin.com/in "[Company English Name]" "sales"
site:linkedin.com/in "[Company English Name]" "export"
site:facebook.com "[Company English Name]"
site:youtube.com "[Company English Name]"
site:instagram.com "[Company English Name]"
site:tiktok.com "[Company English Name]"
"[Company English Name]" "WhatsApp"
```

客户开发：
```text
"[Product]" "[Country]" distributor LinkedIn
site:linkedin.com/in "[Product]" "[Country]" procurement
site:facebook.com "[Product]" "[Country]" dealer
site:youtube.com "[Product]" "[Country]" supplier
"[Product]" "[Country local language]" dealer distributor
```

竞品分析：
```text
"[Competitor]" LinkedIn
"[Competitor]" Facebook
"[Competitor]" YouTube
"[Competitor]" exhibition
"[Competitor]" distributor
"[Competitor]" complaint
```

风险/口碑：
```text
"[Company Name]" complaint
"[Company Name]" review
"[Company Name]" scam
site:reddit.com "[Company Name]"
site:youtube.com "[Company Name]" review
```

中文社媒：
```text
"[中文公司名]" 微信公众号
"[中文公司名]" 公众号 展会
"[中文公司名]" 认证 公众号
"[中文公司名]" 招聘
"[中文公司名]" 抖音
"[中文公司名]" 视频号
"[中文公司名]" 小红书
```

#### 社媒线索独立评分

社媒结果不要并入 Phase 4 的 authority 主排序；单独作为 `social_leads` 线索处理。不要为了社媒提权而修改 `references/authority-domains.json`，避免污染普通事实/技术搜索。

社媒线索按以下维度判断：

| 维度 | 判断重点 |
|---|---|
| 主体一致性 | 名称、Logo、官网、地址、电话是否一致 |
| 活跃度 | 最近更新时间、发帖频率 |
| 互动真实性 | 评论、转发、客户互动是否自然 |
| 人员关联度 | 是否有真实员工、职位、所在地 |
| 海外相关性 | 是否有目标国家、展会、客户、代理商信息 |
| 来源权重 | 官方页 > 员工公开页 > 客户互动 > 第三方转述 |
| 风险信号 | 多主页、僵尸号、口径冲突、投诉集中 |

#### 输出分层术语

统一使用：`已验证事实 / 平台公开口径 / 社媒线索 / 贸易数据线索 / 推测判断 / 待核验项`。

---

## Phase 3: 多源并行检索

### Step 1: Brave（所有模式）

对每个子查询调用 `web_search`。如果意图有 freshness 要求，传 `freshness` 参数：

```
web_search(query="Deno 2.0 latest 2026", freshness="pw")
```

### Step 2: Exa + Tavily + Grok + Firecrawl（Deep / Answer 模式）

对子查询调用 search.py，传入意图和 freshness：

```bash
python3 <search-layer-root>/scripts/search.py \
  --queries "子查询1" "子查询2" "子查询3" \
  --mode deep \
  --intent status \
  --freshness pw \
  --num 5
```

**各模式源参与矩阵**：
| 模式 | Exa | Tavily | Grok | 说明 |
|------|-----|--------|------|------|
| fast | ✅ | ❌ | fallback | Exa 优先；无 Exa key 时用 Grok |
| deep | ✅ | ✅ | ✅ | ✅ | 四源并行；Firecrawl 可返回页面正文 markdown 片段 |
| answer | ❌ | ✅ | ❌ | 仅 Tavily（含 AI answer） |

**参数说明**：
| 参数 | 说明 |
|------|------|
| `--queries` | 多个子查询并行执行（也可用位置参数传单个查询） |
| `--mode` | fast / deep / answer |
| `--intent` | 意图类型，影响评分权重（不传则不评分，行为与 v1 一致） |
| `--freshness` | pd(24h) / pw(周) / pm(月) / py(年) |
| `--domain-boost` | 逗号分隔的域名，匹配的结果权威分 +0.2 |
| `--num` | 每源每查询的结果数 |

**Exa 源说明（两层角色）**：
- **Retrieval lane（默认主路径）**：
  - 默认仍走 `/search`，但不再固定死 `type=auto`
  - 当前最小映射：
    - `resource` → `instant`
    - `status` / `news` → `fast`
    - `exploratory` + `mode=deep` → `deep`
    - 其他 → `auto`
  - 默认附带 `contents.highlights.maxCharacters=1200`，提升 snippet 质量，避免 Exa 结果因空摘要在本地 ranking 中被低估
  - `freshness` 会映射为 Exa `startPublishedDate`，让 status/news 查询和 Tavily/Grok 时间窗口更一致
  - 结果 metadata 中保留 `meta.exaType`，便于观测实际 resolved type
- **Research lane（选择性升级）**：
  - 仅当 query 命中复杂 `comparison / exploratory / status / news` 场景时，在标准候选召回之后追加一段 Exa `type=deep` 研究块，并以 `research` 字段附加到输出
  - `research` 是附加 contract，不替换 `results`，保证旧调用方仍可只读 `results`
  - 当前边界：comparison 需显式对比词/判断词/3+ 子查询；exploratory 需判断/因果/对比词；status/news 需判断/因果词，不因普通多查询扩展误触发
- 暂不把 `deep-reasoning` / `outputSchema` 接进默认主路径，避免基础 search-layer 变成重型 research/synthesis 引擎
- Exa 端点默认是 `https://api.exa.ai/search`；如需自建/代理，可通过 `EXA_API_BASE`/`EXA_API_URL` 或 credentials 文件里的 `exaApiBase` 覆盖（优先搜索：`SEARCH_LAYER_CREDENTIALS` → `OPENCLAW_CREDENTIALS_DIR/search.json` → `./credentials/search.json` → `~/.openclaw/credentials/search.json`；示例：`https://exa.example.com`）

**Firecrawl 源说明**：
- 通过 Firecrawl `/v2/search` 接入，定位为“搜索 + 抓取正文”补充源，尤其适合需要页面正文 markdown/snippet 的调研。
- 仅在 `deep` 模式参与；`fast` 仍保持 Exa/Grok 轻量路径，`answer` 仍由 Tavily 负责 AI answer。
- 默认请求 `scrapeOptions.formats=["markdown"]`，返回内容优先级：`markdown` → `content/text` → `description/snippet`，本地截断到 2000 字符用于排序与合成。
- 兼容 Firecrawl v2 `data.web/news/images` 分组返回结构，自动平铺为统一结果列表。
- `freshness` 会映射为 Firecrawl `tbs`：`pd=qdr:d`、`pw=qdr:w`、`pm=qdr:m`、`py=qdr:y`。
- 需要在 credentials 文件中配置 `firecrawl`，或通过环境变量 `FIRECRAWL_API_KEY` 配置；可用 `FIRECRAWL_API_BASE`/`FIRECRAWL_API_URL` 或 credentials 中的 `firecrawl.apiUrl` 覆盖默认 `https://api.firecrawl.dev/v2/search`。便携包默认支持：`SEARCH_LAYER_CREDENTIALS`、`OPENCLAW_CREDENTIALS_DIR/search.json`、包内 `credentials/search.json`、`~/.openclaw/credentials/search.json`。
- 可用 `--source firecrawl` 单独测试，或 `--source exa,tavily,firecrawl` 临时排除 Grok。
- **正文增强（`--enrich-top`）**：在多源召回、去重、按 intent 打分排序后，对前 N 个 URL 调用 Firecrawl `/v2/scrape` 抓正文，将 `markdown` 截断为最大 `--enrich-max-chars` 字符后写入结果的 `content` 字段，同时设置 `enriched=true` 并在 `source` 末尾追加 `firecrawl-enrich`。例：`--mode deep --intent exploratory --num 5 --enrich-top 3 --enrich-max-chars 4000`。适合深搜/调研头部证据增强；未配置 Firecrawl Key 时会在 `output.enrich` 中返回 warning 并跳过。

**Grok 源说明**：
- 通过 completions API 调用 Grok 模型（X/Twitter 相关默认优先 `grok-4.3`），利用其实时知识返回结构化搜索结果
- 自动检测时间敏感查询并注入当前时间上下文
- 在 deep 模式下与 Exa、Tavily 并行执行
- 需要在 credentials 文件中配置 Grok 的 `apiUrl`、`apiKey`、`model`（或通过环境变量 `GROK_API_URL`、`GROK_API_KEY`、`GROK_MODEL`）；便携包同样支持从 `SEARCH_LAYER_CREDENTIALS`、`OPENCLAW_CREDENTIALS_DIR/search.json`、包内 `credentials/search.json` 自动读取。
- 如果 Grok 配置缺失，自动降级为 Exa + Tavily 双源

### Step 3: 合并

将 Brave 结果与 search.py 输出合并。按 canonical URL 去重，标记来源。

如果 search.py 返回了 `score` 字段，用它排序；Brave 结果没有 score 的，用同样的意图权重公式补算。

---

## Phase 3.5: 引用追踪（Thread Pulling）

当搜索结果中包含 GitHub issue/PR 链接，且意图为 Status 或 Exploratory 时，自动触发引用追踪。

### 自动触发条件

- 意图为 `status` 或 `exploratory`
- 搜索结果中包含 `github.com/.../issues/` 或 `github.com/.../pull/` URL

### 方式 1: search.py --extract-refs（批量）

在搜索结果上直接提取引用图，无需额外调用：

```bash
python3 search.py "OpenClaw config validation bug" --mode deep --intent status --extract-refs
```

输出中会多一个 `refs` 字段，包含每个结果 URL 的引用列表。

也可以跳过搜索，直接对已知 URL 提取引用：

```bash
python3 search.py --extract-refs-urls "https://github.com/owner/repo/issues/123" "https://github.com/owner/repo/issues/456"
```

### 方式 2: fetch-thread（单 URL 深度抓取）

对单个 URL 拉取完整讨论流 + 结构化引用：

```bash
python3 fetch_thread.py "https://github.com/owner/repo/issues/123" --format json
python3 fetch_thread.py "https://github.com/owner/repo/issues/123" --format markdown
python3 fetch_thread.py "https://github.com/owner/repo/issues/123" --extract-refs-only
```

GitHub 场景（issue/PR）：通过 API 拉取正文 + 全部 comments + timeline 事件（cross-references、commits），提取：
- Issue/PR 引用（#123、owner/repo#123）
- Duplicate 标记
- Commit 引用
- 关联 PR/issue（timeline cross-references）
- 外部 URL

通用 web 场景：web fetch + 正则提取引用链接。

### Agent 执行流程

```
Step 1: search-layer 搜索 → 获取初始结果
Step 2: search.py --extract-refs 或 fetch-thread → 提取线索图
Step 3: Agent 筛选高价值线索（LLM 判断哪些值得追踪）
Step 4: fetch-thread 深度抓取每个高价值线索
Step 5: 重复 Step 2-4，直到信息闭环或达到深度限制（建议 max_depth=3）
```

---

## Phase 4: 结果排序

### 评分公式

```
score = w_keyword × keyword_match + w_freshness × freshness_score + w_authority × authority_score
```

权重由意图决定（见 Phase 1 表格）。各分项：

- **keyword_match** (0-1)：查询词在标题+摘要中的覆盖率
- **freshness_score** (0-1)：基于发布日期，越新越高（无日期=0.5）
- **authority_score** (0-1)：基于域名权威等级
  - Tier 1 (1.0): github.com, stackoverflow.com, 官方文档站
  - Tier 2 (0.8): HN, dev.to, 知名技术博客
  - Tier 3 (0.6): Medium, 掘金, InfoQ
  - Tier 4 (0.4): 其他

> 完整域名评分表见 `references/authority-domains.json`

### Domain Boost

通过 `--domain-boost` 参数手动指定需要加权的域名（匹配的结果权威分 +0.2）：
```bash
search.py "query" --mode deep --intent tutorial --domain-boost dev.to,freecodecamp.org
```

推荐搭配：
- Tutorial → `dev.to, freecodecamp.org, realpython.com, baeldung.com`
- Resource → `github.com`
- News → `techcrunch.com, arstechnica.com, theverge.com`

---

## Phase 5: 知识合成

根据结果数量选择合成策略：

### 小结果集（≤5 条）
逐条展示，每条带源标签和评分：
```
1. [Title](url) — snippet... `[brave, exa]` ⭐0.85
2. [Title](url) — snippet... `[tavily]` ⭐0.72
```

### 中结果集（5-15 条）
按主题聚类 + 每组摘要：
```
**主题 A: [描述]**
- [结果1] — 要点... `[source]`
- [结果2] — 要点... `[source]`

**主题 B: [描述]**
- [结果3] — 要点... `[source]`
```

### 大结果集（15+ 条）
高层综述 + Top 5 + 深入提示：
```
[一段综述，概括主要发现]

**Top 5 最相关结果：**
1. ...
2. ...

共找到 N 条结果，覆盖 [源列表]。需要深入哪个方面？
```

### 合成规则
- **先给答案，再列来源**（不要先说"我搜了什么"）
- **按主题聚合，不按来源聚合**（不要"Brave 结果：... Exa 结果：..."）
- **冲突信息显性标注**：不同源说法矛盾时明确指出
- **置信度表达**：
  - 多源一致 + 新鲜 → 直接陈述
  - 单源或较旧 → "根据 [source]，..."
  - 冲突或不确定 → "存在不同说法：A 认为...，B 认为..."

### Firecrawl 辅助脚本

除 `search.py` 内置 Firecrawl Search/Enrich 外，`scripts/` 下还提供独立辅助脚本：

| 脚本 | 能力 | 典型用途 |
|---|---|---|
| `firecrawl_client.py` | 公共认证、endpoint 解析、请求封装 | 供其他脚本复用 |
| `firecrawl_fetch.py` | `/v2/scrape` 单页正文抓取 | 已知 URL 要 markdown/links 正文（known_url） |
| `firecrawl_extract.py` | `/v2/scrape` + `formats=[{"type":"json"}]` 结构化抽取 | 政策字段、公司画像、产品/资质/联系方式提取 |
| `firecrawl_site.py map` | `/v2/map` 网站 URL 摸排 | 先看官网/政府栏目/供应商网站有哪些页面 |
| `firecrawl_site.py crawl` | `/v2/crawl` 站点爬取 | 定向抓取重点站点多页内容 |

常用命令：

```bash
# 已知单个 URL：只要正文 markdown/links（known_url）
python3 scripts/firecrawl_fetch.py "https://example.com/article" --formats markdown,links

# 已知 URL/多个 URL：按自然语言提示抽取字段（新版走 /v2/scrape 的 json format）
python3 scripts/firecrawl_extract.py \
  --url "https://example.com/policy" \
  --prompt "提取政策名称、发布单位、申报对象、申报条件、截止时间、联系方式"

# 可选：同时拿一段 markdown 摘要，方便人工核对
python3 scripts/firecrawl_extract.py \
  --url "https://example.com/company" \
  --prompt "提取公司名称、主营产品、资质认证、联系方式" \
  --include-markdown

# 研究一个网站前，先摸 URL 结构
python3 scripts/firecrawl_site.py map "https://example.com" --limit 50

# 对重点网站做小规模爬取
python3 scripts/firecrawl_site.py crawl "https://example.com" --limit 20 --wait
```

使用边界：
- 已知 URL 且只要正文摘要，优先 `firecrawl_fetch.py`（或在搜索场景用 `search.py --enrich-top`）；需要字段时用 `firecrawl_extract.py`。
- 公司/供应商/竞品深搜，优先 `firecrawl_site.py map`，只对重点栏目/站点 crawl。
- 政策/申报/公告类任务，优先 `firecrawl_extract.py` 抽取固定字段，保留原文链接。
- Firecrawl 报错或额度/频率受限时，回退到 `ws_fetch` / `browser` / 其他搜索源。

---

## 降级策略

- Exa 429/5xx → 继续 Brave + Tavily + Grok
- Tavily 429/5xx → 继续 Brave + Exa + Grok
- Grok 超时/错误 → 继续 Brave + Exa + Tavily
- Firecrawl 429/5xx → 继续 Brave + Exa + Tavily + Grok
- search.py 整体失败 → 仅用 Brave `web_search`（始终可用）
- **永远不要因为某个源失败而阻塞主流程**

---

## 向后兼容

不带 `--intent` 参数时，search.py 行为与 v1 完全一致（无评分，按原始顺序输出）。

现有调用方（如 github-explorer）无需修改。

---

## 快速参考

| 场景 | 命令 |
|------|------|
| 快速事实 | `web_search` + `search.py --mode answer --intent factual` |
| 深度调研 | `web_search` + `search.py --mode deep --intent exploratory` |
| 最新动态 | `web_search(freshness="pw")` + `search.py --mode deep --intent status --freshness pw` |
| 对比分析 | `web_search` × 3 queries + `search.py --queries "A vs B" "A pros" "B pros" --intent comparison` |
| 找资源 | `web_search` + `search.py --mode fast --intent resource` |
