"""Benchmark Ollama models on johnson for a realistic tool-calling call."""
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["OLLAMA_URL"], api_key="ollama",
                timeout=120)
TOOLS = [{"type": "function", "function": {
    "name": "semantic_search", "description": "search emails",
    "parameters": {"type": "object",
                   "properties": {"query": {"type": "string"}},
                   "required": ["query"]}}}]
MSG = [{"role": "user", "content": "Investigate Enron fraud. Search the "
        "emails for evidence of off-book partnerships. Use the tool."}]

for model in ["qwen3:30b-a3b-instruct-2507-q4_K_M", "qwen3:8b",
              "qwen3:4b", "mistral:7b"]:
    try:
        t = time.time()
        r = client.chat.completions.create(model=model, messages=MSG,
                                           tools=TOOLS, max_tokens=150)
        dt = time.time() - t
        tc = r.choices[0].message.tool_calls
        print(f"{model:<38} {dt:5.1f}s  tool_call={'yes' if tc else 'NO'}",
              flush=True)
    except Exception as e:
        print(f"{model:<38} ERROR {str(e)[:50]}", flush=True)
