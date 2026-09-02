from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path


def _load_env_file() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file()


AI_API_KEY = os.getenv("TTK_API_KEY", "")
AI_BASE_URL = os.getenv("TTK_API_BASE_URL", "https://api.ttk.homes/v1").rstrip("/")
AI_MODEL = os.getenv("TTK_MODEL", "[按量计费]deepseek-v4-flash")

SYSTEM_PROMPT = """你是“网络主播与 MCN 机构用工关系评估及权益保障平台”的内嵌 AI 助手。
你可以回答平台使用、网络主播与 MCN 用工关系、三从属性、类劳动者、证据准备、案例检索、合同风险和权益保障相关问题。
回答应清晰、谨慎、专业。涉及法律判断时，应提示用户最终结论需结合具体证据、合同文本和当地裁判规则，不能把你的回答当成正式法律意见。
不要使用 Markdown 格式，不要输出 #、*、**、###、```、表格语法。请用普通中文段落和“1.”“2.”这类纯文本编号回答。
"""


def ask_ai(messages: list[dict], knowledge_context: str = "") -> str:
    if not AI_API_KEY:
        raise RuntimeError("AI API key is not configured.")
    if not AI_BASE_URL.startswith("https://"):
        raise RuntimeError("AI API must use HTTPS.")

    payload = {
        "model": AI_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT + ("\n以下是平台已审核知识，请优先据此回答并明确写出依据名称：\n" + knowledge_context if knowledge_context else "")}, *messages],
        "temperature": 0.35,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{AI_BASE_URL}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            "Accept": "application/json,text/plain,*/*",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"AI service returned {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"AI service is unreachable: {exc.reason}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("AI service returned no answer.")
    message = choices[0].get("message") or {}
    return str(message.get("content") or "").strip()
