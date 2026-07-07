# 检索策略消融评估报告 v3

评估时间：2026-06-25 10:55
可答题：14 | 不可答题：4 | 全库 chunk：958
K_VALUES：[5, 10, 20, 30, 50] | RETRIEVAL_K：50
Reranker 输出：top-8 | 候选池：50
大池消融：BM25@200 → Rerank(no-fusion)@20 | RRF@200 → Rerank(fusion)@20
混合打分：BM25(45%)+Rerank(25%)+Keyword(20%)+Meta(10%)，BM25 top-5 保底 | 不硬截断
Fusion alpha：0.7/0.8 | passage_mode：基线/增强/fusion

## 分阶段召回统计（strict / window chunk_recall）

| 阶段 | strict_chunk_recall | window_chunk_recall | 说明 |
|------|-------------------|-------------------|------|
| Vector @30 | 0.038 | 0.181 | 向量检索 top-30 |
| Vector @50 | 0.080 | 0.323 | 向量检索 top-50 |
| BM25 @30 | 0.883 | 0.954 | BM25 关键词 top-30 |
| BM25 @50 | 0.954 | 0.986 | BM25 关键词 top-50 |
| BM25 @200 | 1.000 | 1.000 | BM25 关键词 top-200 |
| Union @60 | 0.742 | 0.885 | 向量+BM25 去重合并 top-60 |
| RRF @20 | 0.830 | 0.876 | RRF 融合后 top-20 |
| RRF @50 | 0.883 | 0.954 | RRF 融合后 top-50 |
| Rerank @5 | 0.345 | 0.437 | Reranker 精排 top-5 |
| Rerank @10 | 0.580 | 0.761 | Reranker 精排 top-10 |
| Rerank-large @10 | 0.564 | 0.761 | RRF@200→Rerank(fusion) top-10 |
| Rerank-large @20 | 0.794 | 0.886 | RRF@200→Rerank(fusion) top-20 |

## Chunk ID 诊断

- 可答题共 16 题，其中 16 题有 chunk_id 标注，0 题 chunks=0

## 可答题检索指标（十四大策略）

| 指标 | vector_only | hybrid_no_rerank | hybrid_rerank | hybrid_rerank_translate | hybrid_rerank_enhanced | hybrid_rerank_fusion_07 | hybrid_rerank_fusion_08 | bm25_rerank_large | hybrid_rerank_large | hybrid_score | hybrid_score_raw | hybrid_score_translate | mq_rrf | production |
|------|-------------|------------------|---------------|-------------------------|------------------------|-------------------------|-------------------------|-------------------|---------------------|--------------|------------------|------------------------|--------|------------|
| source_recall@5 | 0.571 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 0.964 | 0.964 | 0.964 | 0.964 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| evidence_recall@5 | 0.250 | 0.964 | 1.000 | 1.000 | 0.821 | 0.821 | 0.821 | 0.857 | 0.893 | 0.964 | 0.964 | 0.964 | 1.000 | 0.964 | 🏆 hybrid_rerank
| source_recall@10 | 0.714 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| evidence_recall@10 | 0.393 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 0.857 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| source_recall@20 | 0.821 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| evidence_recall@20 | 0.393 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| source_recall@30 | 0.929 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| evidence_recall@30 | 0.500 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| source_recall@50 | 0.929 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| evidence_recall@50 | 0.679 | 1.000 | 1.000 | 1.000 | 0.964 | 0.964 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.964 | 🏆 hybrid_no_rerank
| source_mrr | 0.418 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 hybrid_rerank
| source_hit@5 | 0.643 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 hybrid_no_rerank
| all_sources_hit@5 | 0.500 | 1.000 | 1.000 | 1.000 | 0.929 | 0.929 | 0.929 | 1.000 | 0.929 | 0.929 | 0.929 | 0.929 | 1.000 | 0.929 | 🏆 hybrid_no_rerank
| keyword_coverage@5 | 0.389 | 0.589 | 0.618 | 0.618 | 0.618 | 0.618 | 0.604 | 0.575 | 0.618 | 0.618 | 0.618 | 0.604 | 0.661 | 0.632 | 🏆 mq_rrf
| source_hit@10 | 0.786 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 hybrid_no_rerank
| all_sources_hit@10 | 0.643 | 1.000 | 1.000 | 1.000 | 0.929 | 0.929 | 0.929 | 1.000 | 0.929 | 1.000 | 1.000 | 1.000 | 1.000 | 0.929 | 🏆 hybrid_no_rerank
| keyword_coverage@10 | 0.518 | 0.632 | 0.646 | 0.646 | 0.632 | 0.618 | 0.618 | 0.618 | 0.632 | 0.646 | 0.646 | 0.646 | 0.661 | 0.646 | 🏆 mq_rrf
| source_hit@20 | 0.857 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 hybrid_no_rerank
| all_sources_hit@20 | 0.786 | 1.000 | 1.000 | 1.000 | 0.929 | 0.929 | 0.929 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.929 | 🏆 hybrid_no_rerank
| keyword_coverage@20 | 0.575 | 0.661 | 0.646 | 0.646 | 0.632 | 0.618 | 0.618 | 0.632 | 0.661 | 0.646 | 0.646 | 0.646 | 0.661 | 0.646 | 🏆 hybrid_no_rerank
| source_hit@30 | 0.929 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 hybrid_no_rerank
| all_sources_hit@30 | 0.929 | 1.000 | 1.000 | 1.000 | 0.929 | 0.929 | 0.929 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.929 | 🏆 hybrid_no_rerank
| keyword_coverage@30 | 0.575 | 0.661 | 0.646 | 0.646 | 0.632 | 0.618 | 0.618 | 0.632 | 0.661 | 0.646 | 0.661 | 0.661 | 0.661 | 0.646 | 🏆 hybrid_no_rerank
| source_hit@50 | 0.929 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 hybrid_no_rerank
| all_sources_hit@50 | 0.929 | 1.000 | 1.000 | 1.000 | 0.929 | 0.929 | 0.929 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.929 | 🏆 hybrid_no_rerank
| keyword_coverage@50 | 0.589 | 0.661 | 0.646 | 0.646 | 0.632 | 0.618 | 0.618 | 0.632 | 0.661 | 0.646 | 0.661 | 0.661 | 0.661 | 0.646 | 🏆 hybrid_no_rerank
| strict_chunk_recall@5 | 0.000 | 0.450 | 0.694 | 0.712 | 0.345 | 0.345 | 0.345 | 0.318 | 0.345 | 0.512 | 0.512 | 0.576 | 0.635 | 0.381 | 🏆 hybrid_rerank_translate
| window_chunk_recall@5 | 0.089 | 0.621 | 0.740 | 0.758 | 0.437 | 0.437 | 0.437 | 0.400 | 0.437 | 0.512 | 0.512 | 0.650 | 0.776 | 0.556 | 🏆 mq_rrf
| strict_chunk_recall@10 | 0.000 | 0.679 | 0.801 | 0.783 | 0.502 | 0.467 | 0.502 | 0.481 | 0.580 | 0.737 | 0.737 | 0.887 | 0.819 | 0.526 | 🏆 hybrid_score_translate
| window_chunk_recall@10 | 0.125 | 0.743 | 0.886 | 0.876 | 0.707 | 0.671 | 0.707 | 0.581 | 0.761 | 0.926 | 0.926 | 0.958 | 0.925 | 0.773 | 🏆 hybrid_score_translate
| strict_chunk_recall@20 | 0.000 | 0.830 | 0.801 | 0.783 | 0.502 | 0.467 | 0.502 | 0.714 | 0.794 | 0.880 | 0.880 | 1.000 | 0.879 | 0.526 | 🏆 hybrid_score_translate
| window_chunk_recall@20 | 0.143 | 0.876 | 0.886 | 0.876 | 0.707 | 0.671 | 0.707 | 0.821 | 0.900 | 0.986 | 0.986 | 1.000 | 0.957 | 0.773 | 🏆 hybrid_score_translate
| strict_chunk_recall@30 | 0.038 | 0.883 | 0.801 | 0.783 | 0.502 | 0.467 | 0.502 | 0.714 | 0.794 | 0.880 | 0.954 | 1.000 | 0.879 | 0.526 | 🏆 hybrid_score_translate
| window_chunk_recall@30 | 0.181 | 0.954 | 0.886 | 0.876 | 0.707 | 0.671 | 0.707 | 0.821 | 0.900 | 0.986 | 0.986 | 1.000 | 0.957 | 0.773 | 🏆 hybrid_score_translate
| strict_chunk_recall@50 | 0.080 | 0.883 | 0.801 | 0.783 | 0.502 | 0.467 | 0.502 | 0.714 | 0.794 | 0.880 | 0.954 | 1.000 | 0.879 | 0.526 | 🏆 hybrid_score_translate
| window_chunk_recall@50 | 0.323 | 0.954 | 0.886 | 0.876 | 0.707 | 0.671 | 0.707 | 0.821 | 0.900 | 0.986 | 0.986 | 1.000 | 0.957 | 0.773 | 🏆 hybrid_score_translate
## 按题型分类统计（hybrid_rerank_fusion_07 @20）

| 类别 | 题数 | source_recall | evidence_recall | source_mrr | strict_chunk_recall | window_chunk_recall |
|------|------|-------------|---------------|-----------|-------------------|-------------------|
| comparison | 2 | 0.750 | 0.750 | 1.000 | 0.600 | 0.700 |
| fact | 2 | 1.000 | 1.000 | 1.000 | 0.500 | 1.000 |
| method | 10 | 1.000 | 1.000 | 1.000 | 0.433 | 0.600 |

## 边界指标（知识边界与证据质量）

### Answerability Accuracy（检索级可答性判断）

- **Answerability Accuracy**: 83.33% （15/18，阈值 fusion_score=0.3）
- **Abstention Rate（正确拒答率）**: 25.00% （1/4 不可答题 max_fusion < 0.3）
- **False Answer Rate（误答率）**: 75.00% （3/4 不可答题被触发）
- **Correct Trigger Rate（可答题正确触发率）**: 100.00% （14/14 可答题 max_fusion >= 0.3）

### 不可答题 — Reranker 触发风险

| ID | Question | Max Reranker Score | Max Fusion Score | 误触发 |
|------|----------|-------------------|-----------------|--------|
| unanswerable_001_en | How does GPT-5 compare against the methods in these papers f | 1.000 | 0.709 | ⚠ 是 |
| unanswerable_002_en | What is the carbon footprint and energy consumption of train | 0.819 | 0.577 | ⚠ 是 |
| unanswerable_001_zh | GPT-5 与这些论文中提出的方法在代码智能和 DNN 安全任务上相比如何？ | 1.000 | 0.707 | ⚠ 是 |
| unanswerable_002_zh | 这些论文中讨论的模型训练的碳排放和能源消耗是多少？ | 0.401 | 0.286 | 否 |

### 可答题 — 证据充分性

- **Avg Max Reranker Score**: 1.000
- **Avg Max Fusion Score**: 0.722
- **Unsupported Evidence Rate（证据不足率）**: 0.00% （0/14 题 max_fusion_score < 0.3）


## 不可答题（知识边界）

不可答题 `should_answer=false`，期望检索不到相关内容。以下指标越低越好：

### 不可答题检索指标

| 指标 | vector_only | hybrid_no_rerank | hybrid_rerank | hybrid_rerank_translate | hybrid_rerank_enhanced | hybrid_rerank_fusion_07 | hybrid_rerank_fusion_08 | bm25_rerank_large | hybrid_rerank_large | hybrid_score | hybrid_score_raw | hybrid_score_translate | mq_rrf | production |
|------|-------------|------------------|---------------|-------------------------|------------------------|-------------------------|-------------------------|-------------------|---------------------|--------------|------------------|------------------------|--------|------------|
| source_recall@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| evidence_recall@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_recall@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| evidence_recall@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_recall@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| evidence_recall@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_recall@30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| evidence_recall@30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_recall@50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| evidence_recall@50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_mrr | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_hit@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| all_sources_hit@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| keyword_coverage@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_hit@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| all_sources_hit@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| keyword_coverage@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_hit@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| all_sources_hit@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| keyword_coverage@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_hit@30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| all_sources_hit@30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| keyword_coverage@30 | 0.083 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| source_hit@50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| all_sources_hit@50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| keyword_coverage@50 | 0.083 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.083 | 0.083 | 0.000 | 0.000 | 🏆 vector_only
| strict_chunk_recall@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| window_chunk_recall@5 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| strict_chunk_recall@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| window_chunk_recall@10 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| strict_chunk_recall@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| window_chunk_recall@20 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| strict_chunk_recall@30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| window_chunk_recall@30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| strict_chunk_recall@50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only
| window_chunk_recall@50 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 🏆 vector_only

---

## RRF-K 消融实验

固定参数：hybrid_k=50 rerank_top_k=8

| rrf_k | strict_chunk_recall@20 | window_chunk_recall@20 |
|------|----------------------|----------------------|
| 10 | 0.830 | 0.894 |
| 20 | 0.862 | 0.958 |
| 30 | 0.826 | 0.958 |
| 60 | 0.790 | 0.887 | ← 当前

---

## 逐题详情（可答题）

- **cross_001_en** [comparison] Compare PoisonedRAG and Machine Against the RAG: how do they each attack RAG sys
  期望来源: ['PoisonedRAG', 'Machine Against the RAG'] | pages: [[2, 3, 4, 5], [2, 3, 4, 5]] | chunks: 5
- **single_001_en** [method] How does AgentSentinel provide end-to-end and real-time security defense for LLM
  期望来源: ['AgentSentinel'] | pages: [[1, 2, 3, 4, 5, 6]] | chunks: 4
- **single_002_en** [method] What is Appatch's automated adaptive prompting approach? How does it improve pro
  期望来源: ['Appatch'] | pages: [[2, 3, 4, 5, 6, 7]] | chunks: 4
- **single_003_en** [method] How does CodeLLM-Devkit contextualize code LLMs? What framework components does 
  期望来源: ['Codellm-Devkit'] | pages: [[1, 2, 3, 4, 5]] | chunks: 2
- **single_004_en** [method] How does BTD recover DNN model specifications from compiled x86 executables? Wha
  期望来源: ['all-Decompiling'] | pages: [[1, 2, 3, 4, 5, 10, 11, 13]] | chunks: 2
- **single_005_en** [fact] What are the main categories and taxonomy of pitfalls when using LLMs for code i
  期望来源: ['Pitfalls'] | pages: [[1, 2, 3, 4, 5, 6, 7, 8]] | chunks: 1
- **single_006_en** [method] How does FlippedRAG achieve black-box opinion manipulation? What is its attack m
  期望来源: ['FlippedRAG'] | pages: [[1, 2, 3, 4, 5, 6]] | chunks: 3
- **cross_001_zh** [comparison] 比较 PoisonedRAG 和 Machine Against the RAG：它们各自如何攻击 RAG 系统？威胁模型的关键区别是什么？
  期望来源: ['PoisonedRAG', 'Machine Against the RAG'] | pages: [[2, 3, 4, 5], [2, 3, 4, 5]] | chunks: 5
- **single_001_zh** [method] AgentSentinel 如何为 LLM 代理提供端到端的实时安全防御？其核心架构是什么？
  期望来源: ['AgentSentinel'] | pages: [[1, 2, 3, 4, 5, 6]] | chunks: 4
- **single_002_zh** [method] Appatch 的自动自适应提示方法是什么？它如何改进程序修复或代码生成？
  期望来源: ['Appatch'] | pages: [[2, 3, 4, 5, 6, 7]] | chunks: 4
- **single_003_zh** [method] CodeLLM-Devkit 如何为代码 LLM 提供上下文？它为改进代码智能任务提供了哪些框架组件？
  期望来源: ['Codellm-Devkit'] | pages: [[1, 2, 3, 4, 5]] | chunks: 2
- **single_004_zh** [method] BTD 如何从编译后的 x86 可执行文件中恢复 DNN 模型规格？它使用了哪些技术，关键评估结果是什么？
  期望来源: ['all-Decompiling'] | pages: [[1, 2, 3, 4, 5, 10, 11, 13]] | chunks: 2
- **single_005_zh** [fact] 根据 Pitfalls 综述，使用 LLM 进行代码智能时的主要陷阱类别和分类体系是什么？
  期望来源: ['Pitfalls'] | pages: [[1, 2, 3, 4, 5, 6, 7, 8]] | chunks: 1
- **single_006_zh** [method] FlippedRAG 如何实现黑盒观点操纵？其攻击方法是什么？需要什么访问权限？
  期望来源: ['FlippedRAG'] | pages: [[1, 2, 3, 4, 5, 6]] | chunks: 3
