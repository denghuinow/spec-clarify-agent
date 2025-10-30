# my_agent/agent.py
from typing import AsyncGenerator, Dict
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.lite_llm import LiteLlm
import os
MODEL = LiteLlm(model=os.getenv("MODEL"))

# --- 1) 需求解析智能体：提取结构化要点，写入 state['req_items'] ---
with open("01需求解析.md", "r", encoding="utf-8") as f:
    req_parse_prompt = f.read()
req_parse = LlmAgent(
    name="ReqParse",
    model=MODEL,
    description="从用户给的自然语言需求中提取结构化需求清单",
    instruction=req_parse_prompt,
    output_key="req_items",  # 自动把最终输出写到 session.state['req_items']
)

# --- 2) 需求挖掘智能体：补全/扩展需求 ---
with open("02需求挖掘.md", "r", encoding="utf-8") as f:
    req_explore_prompt = f.read()
req_explore = LlmAgent(
    name="ReqExplore",
    model=MODEL,
    description="基于当前清单做补全与细化",
    instruction=req_explore_prompt,
    output_key="req_items",  # 用同一个 key 迭代更新
)

# --- 3) 需求澄清智能体：调用工具打分并给出改进建议（写入 state） ---
with open("02需求澄清.md", "r", encoding="utf-8") as f:
    req_clarify_prompt = f.read()
req_clarify = LlmAgent(
    name="ReqClarify",
    model=MODEL,
    description="对照基准SRS进行吻合度评估，给出枚举评分",
    instruction=req_clarify_prompt,
    output_key="critique",
)

# --- 4) 文档生成智能体：把最终清单转为 SRS 完整文档 ---
with open("04文档生成.md", "r", encoding="utf-8") as f:
    doc_generate_prompt = f.read()
doc_generate = LlmAgent(
    name="DocGenerate",
    model=MODEL,
    description="根据最终清单生成 IEEE 29148 风格的 SRS",
    instruction=doc_generate_prompt,
    output_key="srs_md",
)

# --- 多轮迭代环：挖掘 -> 澄清 , 限制轮次 ---
improve_loop = LoopAgent(
    name="ImproveLoop",
    sub_agents=[req_explore, req_clarify],
    max_iterations=5,
)

# --- 管道：解析 -> 多轮改进 -> 生成 ---
root_agent = SequentialAgent(
    name="SRS_Pipeline",
    description="从需求描述到 SRS 的端到端流程",
    sub_agents=[req_parse, improve_loop, doc_generate],
)
