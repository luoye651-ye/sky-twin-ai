"""Small, hand-written retrieval regression set; NOT an LLM answer-accuracy benchmark."""
import json

from rag import INDEX_PATH, MIN_SCORE, ROOT, KnowledgeIndex

CASES = [
    ("禁飞区命中后还能起飞吗", "禁飞区命中条件"),
    ("飞行高度恰好等于限高会违规吗", "限高区与恰好等于限高"),
    ("空域区域最多可以配置多少个", "区域配置约束和规则版本"),
    ("禁飞规则开始和结束时间包含边界吗", "禁飞区命中条件"),
    ("起飞时还会重新校验空域规则吗", "起飞拦截与人工校验"),
    ("怎么创建和分配任务", "创建、分配与执行任务"),
    ("通勤任务对起降场和乘客有什么要求", "创建、分配与执行任务"),
    ("AI巡逻为什么不是每次132张图片", "AI水域巡逻识别演示"),
    ("AI识别漂浮物后会自动生成应急事件吗", "巡逻识别与应急事件的边界"),
    ("上传发现图片应关联什么状态的任务", "提交发现证据"),
    ("发现记录需要人工复核确认吗", "人工复核与事件生成"),
    ("上次侦察还没结束可以重复安排吗", "安排应急侦察与重试"),
    ("应急事件结案需要哪些证据", "结案条件与处置后证据"),
    ("侦察取消或者失败能算处置成功吗", "结案条件与处置后证据"),
    ("可以从通用事件接口直接关闭环境事件吗", "为什么不能直接从通用事件接口结案"),
    ("我的数据库密码是多少", None),
    ("今天杭州天气怎么样", None),
    ("2026年黄金价格是多少", None),
    ("帮我写一首唐诗", None),
    ("新能源电池化学成分是什么", None),
]


def main() -> int:
    index = KnowledgeIndex()
    rows = []
    for question, expected in CASES:
        hits = index.search(question)
        passed = any(hit["section"] == expected for hit in hits) if expected else not hits
        rows.append({"question": question, "expected_section": expected, "passed": passed,
                     "retrieved": [{key: hit[key] for key in ("section", "source", "score")} for hit in hits]})
    report = {
        "scope": "20 hand-written retrieval regression/calibration questions; not held-out evaluation or LLM accuracy",
        "model": index.manifest["model"], "model_revision": index.manifest["revision"],
        "threshold": MIN_SCORE, "chunks": len(index.docs), "top_k": 3,
        "passed": sum(row["passed"] for row in rows), "total": len(rows), "rows": rows,
        "document_hashes": index.manifest["documents"], "code_hashes": index.manifest["code"],
        "paid_llm_calls": 0,
    }
    target = ROOT / "docs/verification/rag-retrieval.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"],
                      "failed_questions": [row["question"] for row in rows if not row["passed"]]}, ensure_ascii=False))
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
