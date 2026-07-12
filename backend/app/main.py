from __future__ import annotations

import os
import time
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.ai_client import ask_ai
from app.auth import change_password, create_session, get_current_user, init_auth, register_user, require_admin, revoke_session
from app.data.content import CASES, QUESTIONS
from app.data.knowledge_seed import LEGAL_KNOWLEDGE
from app.evaluator import RIGHTS_PACKAGES, evaluate_answers
from app.storage import (
    delete_case, delete_evidence, delete_knowledge, delete_matter, evaluation_owned, get_evidence, init_db, list_audit_logs, list_cases, list_evaluations,
    list_knowledge, list_matters, log_action, matter_owned, platform_stats, save_case, save_evaluation,
    save_evidence, save_knowledge, save_matter, update_matter,
)

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".xlsx", ".xls", ".csv"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
AI_RATE_LIMIT = 20
_ai_calls: dict[str, list[float]] = {}
_login_attempts: dict[str, list[float]] = {}


class AuthRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(AuthRequest):
    name: str = Field(min_length=2, max_length=40)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=128)


class EvaluationRequest(BaseModel):
    answers: dict[str, str]


class CaseCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    relation: str = Field(min_length=2, max_length=80)
    year: int | None = Field(default=None, ge=2000, le=2100)
    focus: list[str]
    summary: str = Field(min_length=5, max_length=5000)
    similarity: int | None = Field(default=60, ge=0, le=100)


class CaseBulkCreateRequest(BaseModel):
    cases: list[CaseCreateRequest] = Field(min_length=1, max_length=500)


class KnowledgeCreateRequest(BaseModel):
    category: str = Field(min_length=2, max_length=40)
    title: str = Field(min_length=2, max_length=200)
    summary: str = Field(min_length=5, max_length=5000)
    points: list[str]
    basis: list[str]
    tags: list[str] = Field(default_factory=list)


class AiMessage(BaseModel):
    role: str
    content: str = Field(min_length=1, max_length=6000)


class AiChatRequest(BaseModel):
    messages: list[AiMessage] = Field(min_length=1, max_length=12)


class MatterCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    party_role: str = "主播"
    mcn_name: str = Field(default="", max_length=200)
    dispute_types: list[str] = Field(default_factory=list)
    evaluation_id: str | None = None


class MatterUpdateRequest(BaseModel):
    status: str = "处理中"
    current_step: int = Field(default=1, ge=1, le=4)


app = FastAPI(title="Anchor Rights Platform API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|192\.168\.\d+\.\d+)(:\d+)?|https://[a-z0-9-]+\.trycloudflare\.com",
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db(CASES, LEGAL_KNOWLEDGE)
    init_auth()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/auth/register")
def register(payload: RegisterRequest) -> dict:
    try:
        return register_user(payload.email, payload.name, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/auth/login")
def login(payload: AuthRequest) -> dict:
    key = payload.email.strip().lower()
    now = time.time()
    attempts = [stamp for stamp in _login_attempts.get(key, []) if now - stamp < 900]
    if len(attempts) >= 10:
        raise HTTPException(status_code=429, detail="登录尝试过多，请 15 分钟后再试。")
    try:
        result = create_session(payload.email, payload.password)
        _login_attempts.pop(key, None)
        return result
    except ValueError as exc:
        attempts.append(now); _login_attempts[key] = attempts
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": user}


@app.post("/api/auth/logout")
def logout(authorization: str | None = Header(default=None), _: dict = Depends(get_current_user)) -> dict:
    if authorization:
        revoke_session(authorization.removeprefix("Bearer "))
    return {"loggedOut": True}


@app.post("/api/auth/change-password")
def update_password(payload: PasswordChangeRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        change_password(user["id"], payload.current_password, payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"changed": True, "requiresLogin": True}


@app.get("/api/questions")
def questions() -> dict:
    return {"questions": QUESTIONS, "modelVersion": "2026.07"}


@app.get("/api/rights-packages")
def rights_packages() -> dict:
    return {"rightsPackages": RIGHTS_PACKAGES}


@app.post("/api/evaluate")
def evaluate(payload: EvaluationRequest, user: dict = Depends(get_current_user)) -> dict:
    expected = {q["id"]: {o["id"] for o in q["options"]} for q in QUESTIONS}
    missing = [qid for qid in expected if qid not in payload.answers]
    invalid = [qid for qid, answer in payload.answers.items() if qid not in expected or answer not in expected.get(qid, set())]
    if missing or invalid or len(payload.answers) != len(expected):
        raise HTTPException(status_code=422, detail={"message": "请完成全部 36 道题，并使用有效选项。", "missing": missing, "invalid": invalid})
    result = evaluate_answers(payload.answers)
    evaluation_id = save_evaluation(payload.answers, result, user["id"])
    log_action(user["id"], "生成评估", "evaluation", evaluation_id, result["relationLabel"])
    return {"id": evaluation_id, "result": result}


@app.get("/api/evaluations")
def evaluations(limit: int = 20, user: dict = Depends(get_current_user)) -> dict:
    return {"items": list_evaluations(user["id"], min(max(limit, 1), 100), user["role"] == "admin")}


@app.get("/api/matters")
def matters(user: dict = Depends(get_current_user)) -> dict:
    return {"items": list_matters(user["id"], user["role"] == "admin")}


@app.post("/api/matters")
def create_matter(payload: MatterCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    if payload.evaluation_id and not evaluation_owned(payload.evaluation_id, user["id"], user["role"] == "admin"):
        raise HTTPException(status_code=404, detail="关联评估不存在或无权访问。")
    item = save_matter(payload.model_dump(), user["id"])
    log_action(user["id"], "新建事项", "matter", item["id"], item["title"])
    return {"item": item}


@app.patch("/api/matters/{matter_id}")
def patch_matter(matter_id: str, payload: MatterUpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    if not update_matter(matter_id, payload.model_dump(), user["id"], user["role"] == "admin"):
        raise HTTPException(status_code=404, detail="事项不存在或无权修改。")
    log_action(user["id"], "更新事项进度", "matter", matter_id, f"步骤 {payload.current_step} / {payload.status}")
    return {"updated": True}


@app.delete("/api/matters/{matter_id}")
def remove_matter(matter_id: str, user: dict = Depends(get_current_user)) -> dict:
    files = delete_matter(matter_id, user["id"], user["role"] == "admin")
    if files is None:
        raise HTTPException(status_code=404, detail="事项不存在或无权删除。")
    for stored_name in files:
        path = UPLOAD_DIR / stored_name
        if path.is_file(): path.unlink()
    log_action(user["id"], "删除事项", "matter", matter_id)
    return {"deleted": True}


@app.post("/api/matters/{matter_id}/evidence")
async def upload_evidence(
    matter_id: str, file: UploadFile = File(...), category: str = Form("其他材料"),
    note: str = Form(""), user: dict = Depends(get_current_user),
) -> dict:
    if not matter_owned(matter_id, user["id"], user["role"] == "admin"):
        raise HTTPException(status_code=404, detail="事项不存在或无权添加证据。")
    safe_name = Path(file.filename or "未命名文件").name
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="不支持该文件类型。")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="单个文件不能超过 15MB。")
    user_dir = UPLOAD_DIR / user["id"]
    user_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{extension}"
    (user_dir / stored_name).write_bytes(content)
    item = save_evidence(matter_id, {"name": safe_name, "category": category[:80], "note": note[:1000], "status": "已上传", "stored_name": f"{user['id']}/{stored_name}", "mime_type": file.content_type or "application/octet-stream", "size_bytes": len(content)})
    log_action(user["id"], "上传证据", "evidence", item["id"], safe_name)
    return {"item": item}


@app.get("/api/evidence/{evidence_id}/download")
def download_evidence(evidence_id: str, user: dict = Depends(get_current_user)):
    item = get_evidence(evidence_id, user["id"], user["role"] == "admin")
    if not item or not item["storedName"]:
        raise HTTPException(status_code=404, detail="文件不存在或无权访问。")
    path = (UPLOAD_DIR / item["storedName"]).resolve()
    if not path.is_file() or UPLOAD_DIR.resolve() not in path.parents:
        raise HTTPException(status_code=404, detail="文件不存在。")
    return FileResponse(path, media_type=item["mimeType"], filename=item["name"])


@app.delete("/api/evidence/{evidence_id}")
def remove_evidence(evidence_id: str, user: dict = Depends(get_current_user)) -> dict:
    item = delete_evidence(evidence_id, user["id"], user["role"] == "admin")
    if not item:
        raise HTTPException(status_code=404, detail="证据不存在或无权删除。")
    if item["storedName"]:
        path = UPLOAD_DIR / item["storedName"]
        if path.is_file():
            path.unlink()
    log_action(user["id"], "删除证据", "evidence", evidence_id, item["name"])
    return {"deleted": True}


@app.get("/api/cases")
def cases(keyword: str = "") -> dict:
    return {"items": list_cases(keyword[:100])}


@app.get("/api/legal-knowledge")
def legal_knowledge(keyword: str = "") -> dict:
    return {"items": list_knowledge(keyword[:100])}


@app.post("/api/admin/cases")
def create_case(payload: CaseCreateRequest, _: dict = Depends(require_admin)) -> dict:
    item = save_case(payload.model_dump()); log_action(_["id"], "新增案例", "case", item["id"], item["title"]); return {"item": item}


@app.post("/api/admin/cases/bulk")
def create_cases_bulk(payload: CaseBulkCreateRequest, _: dict = Depends(require_admin)) -> dict:
    items = [save_case(item.model_dump()) for item in payload.cases]
    return {"items": items, "count": len(items)}


@app.delete("/api/admin/cases/{case_id}")
def remove_case(case_id: str, _: dict = Depends(require_admin)) -> dict:
    if not delete_case(case_id):
        raise HTTPException(status_code=404, detail="案例不存在。")
    log_action(_["id"], "删除案例", "case", case_id); return {"deleted": True, "id": case_id}


@app.post("/api/admin/legal-knowledge")
def create_legal_knowledge(payload: KnowledgeCreateRequest, _: dict = Depends(require_admin)) -> dict:
    item = save_knowledge(payload.model_dump()); log_action(_["id"], "新增知识", "knowledge", item["id"], item["title"]); return {"item": item}


@app.delete("/api/admin/legal-knowledge/{knowledge_id}")
def remove_legal_knowledge(knowledge_id: str, user: dict = Depends(require_admin)) -> dict:
    if not delete_knowledge(knowledge_id):
        raise HTTPException(status_code=404, detail="知识条目不存在。")
    log_action(user["id"], "删除知识", "knowledge", knowledge_id)
    return {"deleted": True}


@app.get("/api/admin/stats")
def admin_stats(user: dict = Depends(get_current_user)) -> dict:
    return platform_stats(user["id"], user["role"] == "admin")


@app.get("/api/admin/audit-logs")
def audit_logs(limit: int = 100, _: dict = Depends(require_admin)) -> dict:
    return {"items": list_audit_logs(limit)}


@app.post("/api/ai/chat")
def ai_chat(payload: AiChatRequest, user: dict = Depends(get_current_user)) -> dict:
    now = time.time()
    recent = [stamp for stamp in _ai_calls.get(user["id"], []) if now - stamp < 3600]
    if len(recent) >= AI_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="AI 问答每小时最多 20 次，请稍后再试。")
    recent.append(now); _ai_calls[user["id"]] = recent
    messages = [{"role": item.role, "content": item.content.strip()} for item in payload.messages if item.role in {"user", "assistant"}][-12:]
    if not messages:
        raise HTTPException(status_code=400, detail="请输入问题。")
    try:
        query = messages[-1]["content"]
        knowledge = list_knowledge(query[:100]) or list_knowledge()[:6]
        context = "\n".join(f"- {item['title']}：{item['summary']}；依据：{'；'.join(item['basis'][:3])}" for item in knowledge[:6])
        return {"answer": ask_ai(messages, context)}
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="AI 服务暂时不可用，请稍后重试。") from exc
