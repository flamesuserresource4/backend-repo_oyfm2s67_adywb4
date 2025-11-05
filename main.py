import os
from datetime import datetime
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import BlogPost, CaseStudy, Project, Chat

app = FastAPI(title="Portfolio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


@app.get("/")
def read_root():
    return {"message": "Portfolio Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    return response


# -------- Blog Endpoints --------
@app.get("/blog")
def list_blog_posts() -> List[Dict[str, Any]]:
    docs = get_documents("blogpost")
    docs = [serialize_doc(d) for d in docs]
    docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return docs


@app.post("/blog", status_code=201)
def create_blog_post(post: BlogPost) -> Dict[str, Any]:
    post_id = create_document("blogpost", post)
    return {"id": post_id}


# -------- Case Studies Endpoints --------
@app.get("/case-studies")
def list_case_studies() -> List[Dict[str, Any]]:
    docs = get_documents("casestudy")
    docs = [serialize_doc(d) for d in docs]
    docs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return docs


@app.post("/case-studies", status_code=201)
def create_case_study(case: CaseStudy) -> Dict[str, Any]:
    cid = create_document("casestudy", case)
    return {"id": cid}


# -------- Projects Endpoints --------
@app.get("/projects")
def list_projects() -> List[Dict[str, Any]]:
    docs = get_documents("project")
    docs = [serialize_doc(d) for d in docs]
    # Featured first, then created_at desc
    docs.sort(key=lambda x: (not x.get("featured", False), x.get("created_at", "")), reverse=False)
    return docs


@app.post("/projects", status_code=201)
def create_project(proj: Project) -> Dict[str, Any]:
    pid = create_document("project", proj)
    return {"id": pid}


# -------- AI Assistant Endpoint --------
class ChatRequest(BaseModel):
    message: str


@app.post("/assistant/chat")
def assistant_chat(req: ChatRequest) -> Dict[str, str]:
    """Very simple keyword-based assistant that searches your content and replies.
    This is real working without external APIs.
    """
    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty message")

    # Save user message
    create_document("chat", Chat(role="user", message=user_msg))

    # Build a small context from blog posts, case studies and projects
    def fetch_titles(col: str, fields: List[str]) -> List[Dict[str, Any]]:
        docs = get_documents(col)
        items: List[Dict[str, Any]] = []
        for d in docs:
            s = serialize_doc(d)
            snippet_parts = []
            for f in fields:
                val = s.get(f)
                if isinstance(val, list):
                    snippet_parts.append(", ".join(map(str, val)))
                elif isinstance(val, dict):
                    snippet_parts.append(", ".join(f"{k}: {v}" for k, v in val.items()))
                elif isinstance(val, str):
                    snippet_parts.append(val)
            s["snippet"] = " \u2022 ".join([p[:200] for p in snippet_parts if p])
            items.append(s)
        return items

    blogs = fetch_titles("blogpost", ["title", "tags", "content"])[:10]
    cases = fetch_titles("casestudy", ["title", "summary", "impact"])[:10]
    projs = fetch_titles("project", ["title", "description", "tech_stack"])[:10]

    corpus = blogs + cases + projs

    # Simple scoring by keyword overlap
    tokens = {t.lower() for t in user_msg.split() if len(t) > 2}
    def score(item: Dict[str, Any]) -> int:
        text = (item.get("title", "") + " " + item.get("snippet", "")).lower()
        return sum(1 for t in tokens if t in text)

    best = sorted(corpus, key=score, reverse=True)[:3]

    if not best:
        reply = (
            "Thanks for reaching out! I build production-grade web apps, AI features, and clean UI systems. "
            "Ask about projects, case studies, or share your idea and I’ll outline an approach."
        )
    else:
        lines = [
            "Here are some highlights that match what you asked:",
        ]
        for item in best:
            line = f"- {item.get('title', 'Untitled')}: {item.get('snippet', '')}"
            lines.append(line)
        lines.append(
            "Want a deeper dive or a quick estimate? I can outline a plan step-by-step."
        )
        reply = "\n".join(lines)

    # Save assistant message
    create_document("chat", Chat(role="assistant", message=reply))

    return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
