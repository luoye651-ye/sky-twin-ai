"""Local retrieval coverage checks, not an answer accuracy benchmark."""
import json
from rag import ROOT, KnowledgeIndex

CASES=[
    ('上传图片后如何运行模型检测并提交发现', '上传图片分析与人工发现'),
    ('原始模型预测框和人工选择框会分别保留吗', '模型分析与事件追溯'),
    ('分析记录已经关联发现，还能重复使用吗', '模型分析与事件追溯'),
    ('无人机电量和载重能直接证明任务可以执行吗', '无人机电量载重与仿真边界'),
    ('调度方案过期或网络中断之后怎么恢复', '调度预览失败与恢复'),
    ('连续对话保留几轮，多久过期', '连续对话与地图联动'),
    ('清空会话或重新登录后还会记住之前的对话吗', '连续对话与地图联动'),
    ('助手知识索引过期要如何修复', 'AI服务故障排查'),
]
def main():
    index=KnowledgeIndex();rows=[]
    for question,expected in CASES:
        hits=index.search(question)
        rows.append(dict(question=question,expected=expected,passed=any(hit['section']==expected for hit in hits),
            retrieved=[dict(section=hit['section'],score=hit['score'],source=hit['source']) for hit in hits]))
    report=dict(scope='Eight feature retrieval coverage cases; not held-out or LLM accuracy',
        passed=sum(row['passed'] for row in rows),total=len(rows),rows=rows)
    (ROOT/'docs/verification/knowledge-extension.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['passed']==len(rows) else 1
if __name__=='__main__':raise SystemExit(main())
