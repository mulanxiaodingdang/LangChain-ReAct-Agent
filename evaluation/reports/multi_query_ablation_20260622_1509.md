# Multi-Query 检索策略消融评估报告

**评估时间**: 2026-06-22 15:09
**数据集**: `rag_eval_20.jsonl` (16 answerable)
**Multi-Query 配额**: per-entity BM25=15, Vector=5, min=3, pool=200
**K_VALUES**: [5, 10, 20, 30, 50]
**候选池**: Multi-Query → round-robin 200 docs → 各策略后处理

## 分阶段召回统计（strict / window chunk_recall）

| 阶段 | strict_chunk_recall | window_chunk_recall | 说明 |
|------|-------------------|-------------------|------|
| MQ-BM25 @30 | 0.815 | 0.911 | per-entity BM25 合并 top-30 |
| MQ-BM25 @50 | 0.815 | 0.911 | per-entity BM25 合并 top-50 |
| MQ Pool @50 | 0.815 | 0.932 | round-robin pool top-50 |
| MQ Pool @100 | 0.815 | 0.932 | round-robin pool top-100 |
| MQ Pool @200 | 0.815 | 0.932 | round-robin pool top-200 |
| MQ Rerank @5 | 0.277 | 0.371 | pool→Reranker(fusion) top-5 |
| MQ Rerank @10 | 0.484 | 0.625 | pool→Reranker(fusion) top-10 |
| MQ Rerank @20 | 0.706 | 0.844 | pool→Reranker(fusion) top-20 |

## 可答题检索指标（Multi-Query 全策略）

| 指标 | mq_pool@50 | mq_pool@100 | mq_pool@200 | mq_rerank@8 | mq_rerank@20 | mq_fusion07@8 | mq_fusion07@20 | mq_fusion08@8 | mq_hybrid_score |
|------|------------|-------------|-------------|-------------|--------------|---------------|----------------|---------------|-----------------|
| source_recall@5 | 1.000 | 1.000 | 1.000 | 0.938 | 0.938 | 0.875 | 0.875 | 0.875 | 0.906 | 🏆 mq_pool@50
| evidence_recall@5 | 0.771 | 0.771 | 0.771 | 0.917 | 0.917 | 0.854 | 0.854 | 0.854 | 0.885 | 🏆 mq_rerank@8
| source_recall@10 | 1.000 | 1.000 | 1.000 | 0.958 | 0.958 | 0.906 | 0.938 | 0.906 | 0.938 | 🏆 mq_pool@50
| evidence_recall@10 | 0.958 | 0.958 | 0.958 | 0.958 | 0.958 | 0.854 | 0.938 | 0.854 | 0.938 | 🏆 mq_pool@50
| source_recall@20 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.906 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| evidence_recall@20 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.854 | 0.958 | 0.854 | 0.958 | 🏆 mq_pool@50
| source_recall@30 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.906 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| evidence_recall@30 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.854 | 0.958 | 0.854 | 0.958 | 🏆 mq_pool@50
| source_recall@50 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.906 | 0.958 | 0.906 | 0.958 | 🏆 mq_pool@50
| evidence_recall@50 | 1.000 | 1.000 | 1.000 | 0.958 | 1.000 | 0.854 | 0.958 | 0.854 | 0.958 | 🏆 mq_pool@50
| source_mrr | 0.938 | 0.938 | 0.938 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_rerank@8
| source_hit@5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@5 | 1.000 | 1.000 | 1.000 | 0.875 | 0.875 | 0.750 | 0.750 | 0.750 | 0.812 | 🏆 mq_pool@50
| keyword_coverage@5 | 0.631 | 0.631 | 0.631 | 0.644 | 0.644 | 0.603 | 0.603 | 0.603 | 0.631 | 🏆 mq_rerank@8
| source_hit@10 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@10 | 1.000 | 1.000 | 1.000 | 0.875 | 0.875 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@10 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.631 | 0.603 | 0.656 | 🏆 mq_pool@50
| source_hit@20 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@20 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@20 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.644 | 0.603 | 0.656 | 🏆 mq_pool@50
| source_hit@30 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@30 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@30 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.644 | 0.603 | 0.656 | 🏆 mq_pool@50
| source_hit@50 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 🏆 mq_pool@50
| all_sources_hit@50 | 1.000 | 1.000 | 1.000 | 0.875 | 1.000 | 0.812 | 0.875 | 0.812 | 0.875 | 🏆 mq_pool@50
| keyword_coverage@50 | 0.656 | 0.656 | 0.656 | 0.656 | 0.656 | 0.603 | 0.644 | 0.603 | 0.656 | 🏆 mq_pool@50
| strict_chunk_recall@5 | 0.357 | 0.357 | 0.357 | 0.428 | 0.428 | 0.285 | 0.293 | 0.293 | 0.393 | 🏆 mq_rerank@8
| window_chunk_recall@5 | 0.404 | 0.404 | 0.404 | 0.506 | 0.506 | 0.358 | 0.366 | 0.345 | 0.490 | 🏆 mq_rerank@8
| strict_chunk_recall@10 | 0.534 | 0.534 | 0.534 | 0.565 | 0.615 | 0.432 | 0.484 | 0.422 | 0.612 | 🏆 mq_rerank@20
| window_chunk_recall@10 | 0.672 | 0.672 | 0.672 | 0.680 | 0.721 | 0.552 | 0.625 | 0.552 | 0.745 | 🏆 mq_hybrid_score
| strict_chunk_recall@20 | 0.758 | 0.758 | 0.758 | 0.565 | 0.776 | 0.432 | 0.706 | 0.422 | 0.755 | 🏆 mq_rerank@20
| window_chunk_recall@20 | 0.852 | 0.852 | 0.852 | 0.680 | 0.862 | 0.552 | 0.844 | 0.552 | 0.849 | 🏆 mq_rerank@20
| strict_chunk_recall@30 | 0.805 | 0.805 | 0.805 | 0.565 | 0.776 | 0.432 | 0.706 | 0.422 | 0.755 | 🏆 mq_pool@50
| window_chunk_recall@30 | 0.901 | 0.901 | 0.901 | 0.680 | 0.862 | 0.552 | 0.844 | 0.552 | 0.849 | 🏆 mq_pool@50
| strict_chunk_recall@50 | 0.815 | 0.815 | 0.815 | 0.565 | 0.776 | 0.432 | 0.706 | 0.422 | 0.755 | 🏆 mq_pool@50
| window_chunk_recall@50 | 0.932 | 0.932 | 0.932 | 0.680 | 0.862 | 0.552 | 0.844 | 0.552 | 0.849 | 🏆 mq_pool@50

## 按题型分类统计（mq_fusion07@8 @20）

| 类别 | 题数 | source_recall | evidence_recall | source_mrr | strict_chunk | window_chunk |
|------|------|-------------|---------------|-----------|-------------|-------------|
| comparison | 4 | 0.625 | 0.417 | 1.000 | 0.312 | 0.375 |
| fact | 2 | 1.000 | 1.000 | 1.000 | 0.500 | 0.500 |
| method | 10 | 1.000 | 1.000 | 1.000 | 0.467 | 0.633 |

## 逐题详情（可答题）

- **cross_001_en** [comparison] pool=29 strict@5=0.25 strict@20=0.25
- **cross_002_en** [comparison] pool=33 strict@5=0.38 strict@20=0.50
- **single_001_en** [method] pool=38 strict@5=0.33 strict@20=0.50
- **single_002_en** [method] pool=27 strict@5=0.33 strict@20=0.67
- **single_003_en** [method] pool=37 strict@5=1.00 strict@20=1.00
- **single_004_en** [method] pool=31 strict@5=0.00 strict@20=0.17
- **single_005_en** [fact] pool=33 strict@5=0.50 strict@20=0.83
- **single_006_en** [method] pool=39 strict@5=0.00 strict@20=0.00
- **cross_001_zh** [comparison] pool=30 strict@5=0.38 strict@20=0.50
- **cross_002_zh** [comparison] pool=36 strict@5=0.38 strict@20=0.38
- **single_001_zh** [method] pool=30 strict@5=0.33 strict@20=0.50
- **single_002_zh** [method] pool=51 strict@5=0.00 strict@20=0.00
- **single_003_zh** [method] pool=36 strict@5=1.00 strict@20=1.00
- **single_004_zh** [method] pool=35 strict@5=0.00 strict@20=0.33
- **single_005_zh** [fact] pool=28 strict@5=0.67 strict@20=0.83
- **single_006_zh** [method] pool=39 strict@5=0.17 strict@20=0.17
