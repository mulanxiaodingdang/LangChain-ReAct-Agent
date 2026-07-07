# Multi-Query 检索策略消融评估报告

**评估时间**: 2026-06-22 16:17
**数据集**: `rag_eval_20.jsonl` (16 answerable)
**Multi-Query 配额**: per-entity BM25=15, Vector=5, min=3, pool=200
**K_VALUES**: [5, 10, 20, 30, 50]
**候选池**: Multi-Query → round-robin 200 docs → 各策略后处理

## 分阶段召回统计（strict / window chunk_recall）

| 阶段 | strict_chunk_recall | window_chunk_recall | 说明 |
|------|-------------------|-------------------|------|
| MQ-BM25 @30 | 0.825 | 0.897 | per-entity BM25 合并 top-30 |
| MQ-BM25 @50 | 0.825 | 0.897 | per-entity BM25 合并 top-50 |
| MQ Pool @50 | 0.825 | 0.928 | round-robin pool top-50 |
| MQ Pool @100 | 0.825 | 0.928 | round-robin pool top-100 |
| MQ Pool @200 | 0.825 | 0.928 | round-robin pool top-200 |
| MQ Rerank @5 | 0.285 | 0.336 | pool→Reranker(fusion) top-5 |
| MQ Rerank @10 | 0.524 | 0.631 | pool→Reranker(fusion) top-10 |
| MQ Rerank @20 | 0.724 | 0.853 | pool→Reranker(fusion) top-20 |

## 可答题检索指标（Multi-Query 全策略）

| 指标 | mq_pool@50 | mq_pool@100 | mq_pool@200 | mq_rerank@8 | mq_rerank@20 | mq_fusion07@8 | mq_fusion07@20 | mq_fusion08@8 | mq_hybrid_score |
|------|------------|-------------|-------------|-------------|--------------|---------------|----------------|---------------|-----------------|
| source_recall@5 | 1.000 | 1.000 | 1.000 | 0.938 | 0.938 | 0.875 | 0.875 | 0.875 | 0.906 | 🏆 mq_pool@50
| evidence_recall@5 | 0.771 | 0.771 | 0.771 | 0.917 | 0.917 | 0.854 | 0.854 | 0.854 | 0.885 | 🏆 mq_rerank@8
| source_recall@10 | 1.000 | 1.000 | 1.000 | 0.958 | 0.958 | 0.906 | 0.938 | 0.906 | 0.938 | 🏆 mq_pool@50
| evidence_recall@10 | 0.958 | 0.958 | 0.958 | 0.958 | 0.958 | 0.854 | 0.938 | 0.906 | 0.938 | 🏆 mq_pool@50
| source_recall@20 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.906 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| evidence_recall@20 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.854 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| source_recall@30 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.906 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| evidence_recall@30 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.854 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| source_recall@50 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.906 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| evidence_recall@50 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.854 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| source_mrr | 0.938 | 0.938 | 0.938 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_rerank@8
| source_hit@5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@5 | 1.000 | 1.000 | 1.000 | 0.875 | 0.875 | 0.750 | 0.750 | 0.750 | 0.812 | 🏆 mq_pool@50
| keyword_coverage@5 | 0.631 | 0.631 | 0.631 | 0.644 | 0.644 | 0.603 | 0.603 | 0.603 | 0.631 | 🏆 mq_rerank@8
| source_hit@10 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@10 | 1.000 | 1.000 | 1.000 | 0.875 | 0.875 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@10 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.631 | 0.603 | 0.656 | 🏆 mq_pool@50
| source_hit@20 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@20 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@20 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.656 | 0.603 | 0.656 | 🏆 mq_pool@50
| source_hit@30 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@30 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@30 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.656 | 0.603 | 0.656 | 🏆 mq_pool@50
| source_hit@50 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@50 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@50 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.656 | 0.603 | 0.656 | 🏆 mq_pool@50
| strict_chunk_recall@5 | 0.319 | 0.319 | 0.319 | 0.435 | 0.435 | 0.283 | 0.296 | 0.285 | 0.406 | 🏆 mq_rerank@8
| window_chunk_recall@5 | 0.350 | 0.350 | 0.350 | 0.493 | 0.493 | 0.347 | 0.347 | 0.324 | 0.481 | 🏆 mq_rerank@8
| strict_chunk_recall@10 | 0.523 | 0.523 | 0.523 | 0.648 | 0.658 | 0.447 | 0.514 | 0.462 | 0.660 | 🏆 mq_hybrid_score
| window_chunk_recall@10 | 0.636 | 0.636 | 0.636 | 0.713 | 0.738 | 0.554 | 0.647 | 0.580 | 0.767 | 🏆 mq_hybrid_score
| strict_chunk_recall@20 | 0.765 | 0.765 | 0.765 | 0.648 | 0.773 | 0.447 | 0.745 | 0.462 | 0.806 | 🏆 mq_hybrid_score
| window_chunk_recall@20 | 0.836 | 0.836 | 0.836 | 0.713 | 0.845 | 0.554 | 0.874 | 0.580 | 0.860 | 🏆 mq_fusion07@20
| strict_chunk_recall@30 | 0.812 | 0.812 | 0.812 | 0.648 | 0.773 | 0.447 | 0.745 | 0.462 | 0.806 | 🏆 mq_pool@50
| window_chunk_recall@30 | 0.884 | 0.884 | 0.884 | 0.713 | 0.845 | 0.554 | 0.874 | 0.580 | 0.860 | 🏆 mq_pool@50
| strict_chunk_recall@50 | 0.825 | 0.825 | 0.825 | 0.648 | 0.773 | 0.447 | 0.745 | 0.462 | 0.806 | 🏆 mq_pool@50
| window_chunk_recall@50 | 0.928 | 0.928 | 0.928 | 0.713 | 0.845 | 0.554 | 0.874 | 0.580 | 0.860 | 🏆 mq_pool@50

## 按题型分类统计（mq_fusion07@8 @20）

| 类别 | 题数 | source_recall | evidence_recall | source_mrr | strict_chunk | window_chunk |
|------|------|-------------|---------------|-----------|-------------|-------------|
| comparison | 4 | 0.625 | 0.417 | 1.000 | 0.250 | 0.375 |
| fact | 2 | 1.000 | 1.000 | 1.000 | 0.667 | 0.667 |
| method | 10 | 1.000 | 1.000 | 1.000 | 0.482 | 0.603 |

## 逐题详情（可答题）

- **cross_001_en** [comparison] pool=30 strict@5=0.25 strict@20=0.25
- **cross_002_en** [comparison] pool=33 strict@5=0.33 strict@20=0.50
- **single_001_en** [method] pool=38 strict@5=0.33 strict@20=0.50
- **single_002_en** [method] pool=27 strict@5=0.40 strict@20=0.80
- **single_003_en** [method] pool=37 strict@5=1.00 strict@20=1.00
- **single_004_en** [method] pool=31 strict@5=0.00 strict@20=0.25
- **single_005_en** [fact] pool=33 strict@5=0.33 strict@20=0.67
- **single_006_en** [method] pool=38 strict@5=0.00 strict@20=0.00
- **cross_001_zh** [comparison] pool=30 strict@5=0.25 strict@20=0.25
- **cross_002_zh** [comparison] pool=32 strict@5=0.33 strict@20=0.33
- **single_001_zh** [method] pool=30 strict@5=0.33 strict@20=0.50
- **single_002_zh** [method] pool=52 strict@5=0.00 strict@20=0.00
- **single_003_zh** [method] pool=35 strict@5=1.00 strict@20=1.00
- **single_004_zh** [method] pool=35 strict@5=0.00 strict@20=0.25
- **single_005_zh** [fact] pool=29 strict@5=0.33 strict@20=0.67
- **single_006_zh** [method] pool=39 strict@5=0.20 strict@20=0.20
