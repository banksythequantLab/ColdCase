"""Verify qwen3:30b-a3b handles OpenAI-style tool calls via Ollama."""
import json
import urllib.request

payload = {
    "model": "qwen3:30b-a3b-instruct-2507-q4_K_M",
    "messages": [{"role": "user", "content":
                  "Find emails about off-book partnerships. Use the tool."}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "semantic_search",
            "description": "Semantic search over the email corpus",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"},
                               "k": {"type": "integer"}},
                "required": ["query"],
            },
        },
    }],
    "max_tokens": 200,
}
req = urllib.request.Request(
    "http://johnson:11434/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=180) as r:
    msg = json.load(r)["choices"][0]["message"]
print("tool_calls:", json.dumps(msg.get("tool_calls"), indent=1)[:400])
