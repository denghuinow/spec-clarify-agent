# my_agent/agent.py
from typing import AsyncGenerator, Dict
from google.adk.agents import LlmAgent, SequentialAgent, LoopAgent, BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.lite_llm import LiteLlm
import os
# 从环境变量获取模型，如果未设置则使用默认值
model_name = os.getenv("MODEL", "gpt-3.5-turbo")
MODEL = LiteLlm(model=model_name)

current_dir = os.path.dirname(__file__)
# --- 需求挖掘智能体（合并解析功能）：负责首轮结构化与迭代完善 ---
with open(os.path.join(current_dir, "prompts", "02需求挖掘.md"), "r", encoding="utf-8") as f:
    req_explore_prompt = f.read()
req_explore = LlmAgent(
    name="ReqExplore",
    model=MODEL,
    description="从零开始提取需求并基于澄清评分迭代补全与细化",
    instruction=req_explore_prompt,
    output_key="req_items",  # 用同一个 key 迭代更新
)

# --- 需求澄清智能体：调用工具打分并给出改进建议（写入 state） ---
with open(os.path.join(current_dir, "reference_srs", "2009 - library.doc.md"), "r", encoding="utf-8") as f:
    reference_srs = f.read()
with open(os.path.join(current_dir, "prompts", "03需求澄清.md"), "r", encoding="utf-8") as f:
    req_clarify_prompt = f.read()

# 将 reference_srs 变量注入到 prompt 中
req_clarify_prompt = req_clarify_prompt.replace("{reference_srs}", reference_srs)

req_clarify = LlmAgent(
    name="ReqClarify",
    model=MODEL,
    description="对照基准SRS进行吻合度评估，给出枚举评分",
    instruction=req_clarify_prompt,
    output_key="critique",
)

# --- 4) 文档生成智能体：把最终清单转为 SRS 完整文档 ---
with open(os.path.join(current_dir, "prompts", "04文档生成.md"), "r", encoding="utf-8") as f:
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

# --- 管道：多轮改进 -> 生成 ---
root_agent = SequentialAgent(
    name="SRS_Pipeline",
    description="从需求描述到 SRS 的端到端流程",
    sub_agents=[improve_loop, doc_generate],
)
