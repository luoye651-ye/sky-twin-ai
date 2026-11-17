"""Local operational-topic retrieval coverage, not LLM answer accuracy."""
import json
from rag import ROOT, KnowledgeIndex

CASES = [
    ('失败任务重试会删除原来的轨迹和任务吗', '失败任务重试与待处理提醒'),
    ('维护停用和充电结束后如何恢复电量，谁可以操作', '资源充电维护与站点容量'),
    ('通勤班次预约如何避免并发超卖，生成任务后还能订座吗', '通勤班次预约与取消'),
    ('报告草稿审核前证据改变了怎么办，旧版本还在吗', '历史业务查询与报告草稿'),
    ('候选绕行会自动保存航线吗，包含建筑物避障吗', '自动候选绕行与保存'),
]


def main():
    index = KnowledgeIndex()
    rows = []
    for question, expected in CASES:
        hits = index.search(question)
        rows.append(dict(question=question, expected=expected,
                         passed=any(hit['section'] == expected for hit in hits),
                         retrieved=[dict(section=hit['section'], score=hit['score']) for hit in hits]))
    report = dict(scope='Five new topic coverage checks, not held-out or LLM accuracy',
                  passed=sum(row['passed'] for row in rows), total=len(rows), rows=rows)
    (ROOT / 'docs/verification/operations-knowledge.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['passed'] == len(rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
