# Test: manual agent labels

Người chấm: tác giả (xem mục phương pháp trong báo cáo).

## test_dense_k3

- Context 0/1/2: 0/0/5 (trung bình 2.00/2, n=5)
- Grounded answer 0/1/2: 0/0/5 (trung bình 2.00/2)
- agent_metrics.py:

```json
{
  "split": "test",
  "cases": 7,
  "provider_errors": 0,
  "tool_use": {
    "n": 7,
    "N": 7
  },
  "grounded_answer": {
    "0": 0,
    "1": 0,
    "2": 5,
    "N": 5,
    "mean": 2.0
  },
  "citation_validity": {
    "n": 8,
    "N": 8
  },
  "answer_citation_coverage": {
    "n": 5,
    "N": 5
  },
  "abstention": {
    "n": 2,
    "N": 2
  },
  "false_abstention": {
    "n": 0,
    "N": 5
  }
}
```

## test_hybrid_rrf_k3

- Context 0/1/2: 1/0/4 (trung bình 1.60/2, n=5)
- Grounded answer 0/1/2: 1/0/4 (trung bình 1.60/2)
- agent_metrics.py:

```json
{
  "split": "test",
  "cases": 7,
  "provider_errors": 0,
  "tool_use": {
    "n": 7,
    "N": 7
  },
  "grounded_answer": {
    "0": 1,
    "1": 0,
    "2": 4,
    "N": 5,
    "mean": 1.6
  },
  "citation_validity": {
    "n": 6,
    "N": 6
  },
  "answer_citation_coverage": {
    "n": 4,
    "N": 4
  },
  "abstention": {
    "n": 2,
    "N": 2
  },
  "false_abstention": {
    "n": 1,
    "N": 5
  }
}
```
