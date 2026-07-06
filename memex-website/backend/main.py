import os
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
SECRET_KEY = os.getenv("SECRET_KEY", "website_secret_change_me")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE = 60 * 24

DB_PATH = "/app/data/website.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ContentModel(Base):
    __tablename__ = "content"
    key = Column(String(80), primary_key=True)
    value = Column(Text, default="")


class WikiPageModel(Base):
    __tablename__ = "wiki_pages"
    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(120), unique=True, nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    published = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

# Seed default content
with engine.connect() as conn:
    from sqlalchemy import text
    result = conn.execute(text("SELECT COUNT(*) FROM content")).fetchone()
    if result[0] == 0:
        defaults = {
            "hero_title": "Memex",
            "hero_subtitle": "Your personal link collection, visualized as a mind map.",
            "hero_cta": "View on GitHub",
            "hero_cta_url": "",
            "features": '[{"icon":"🗺","title":"Mind Map","desc":"Interactive D3.js force-directed graph with zoom, pan, and collapsible nodes"},{"icon":"📱","title":"Mobile Ready","desc":"Responsive card grid with search, sort, pagination, and tag filtering"},{"icon":"👥","title":"Federation","desc":"Connect friend instances and browse shared links read-only"},{"icon":"🤖","title":"Android App","desc":"Share links from any app directly to your server"},{"icon":"🧩","title":"Browser Extension","desc":"One-click save from Chrome, Edge, or Firefox"},{"icon":"🎭","title":"5 Themes","desc":"Dark Orange, Cyberpunk Blue, Minimal Green, Purple Haze, Rose Gold"}]',
            "screenshots": '["screenshots/main-page-with-links.PNG","screenshots/main-page-with-links-pinterest-view.PNG","screenshots/memex-admin-page.PNG","screenshots/memex-admin-page-links-view.PNG","screenshots/memex-admin-page-friends-shared-instances-setup.PNG","screenshots/android-companion-screenshot.jpg","screenshots/wallpaper-view.PNG"]',
            "download_text": "Download & Deploy",
            "footer_text": "Built by ironyLabs",
        }
        for k, v in defaults.items():
            conn.execute(text("INSERT INTO content (key, value) VALUES (:k, :v)"), {"k": k, "v": v})
        conn.commit()
        # Seed a default wiki page
        conn.execute(text("INSERT INTO wiki_pages (slug, title, body, sort_order) VALUES ('getting-started', 'Getting Started', '# Getting Started\n\nDeploy Memex with Docker Compose:\n\n```bash\ncp .env.example .env\nnano .env\ndocker compose up -d --build\n```\n\nOpen `http://localhost:8098` to view your mind map.', 1)"))
        conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
HASHED_PW = pwd_ctx.hash(ADMIN_PASSWORD)


def get_current_admin(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(status_code=401)
    return "admin"


app = FastAPI(title="Memex Website API", root_path="/api")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="/app/static"), name="static")


# ── Public ────────────────────────────────────────────────────────────────────
@app.get("/content")
def get_all_content(db: Session = Depends(get_db)):
    rows = db.query(ContentModel).all()
    return {r.key: r.value for r in rows}


@app.get("/content/{key}")
def get_content(key: str, db: Session = Depends(get_db)):
    row = db.query(ContentModel).filter(ContentModel.key == key).first()
    return {"key": key, "value": row.value if row else ""}


@app.get("/wiki")
def get_wiki_pages(db: Session = Depends(get_db)):
    pages = db.query(WikiPageModel).filter(WikiPageModel.published == True).order_by(WikiPageModel.sort_order).all()
    return [{"id": p.id, "slug": p.slug, "title": p.title, "sort_order": p.sort_order} for p in pages]


@app.get("/wiki/{slug}")
def get_wiki_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(WikiPageModel).filter(WikiPageModel.slug == slug, WikiPageModel.published == True).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"id": page.id, "slug": page.slug, "title": page.title, "body": page.body, "updated_at": page.updated_at.isoformat() if page.updated_at else ""}


@app.get("/github-stars")
def get_github_stars():
    return {"repo": GITHUB_REPO}


# ── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/auth/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "admin" or not pwd_ctx.verify(form_data.password, HASHED_PW):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = jwt.encode({"sub": "admin", "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}


# ── Admin ─────────────────────────────────────────────────────────────────────
@app.put("/admin/content/{key}", dependencies=[Depends(get_current_admin)])
def set_content(key: str, payload: dict, db: Session = Depends(get_db)):
    value = payload.get("value", "")
    row = db.query(ContentModel).filter(ContentModel.key == key).first()
    if row:
        row.value = value
    else:
        db.add(ContentModel(key=key, value=value))
    db.commit()
    return {"ok": True}


@app.get("/admin/wiki", dependencies=[Depends(get_current_admin)])
def admin_list_wiki(db: Session = Depends(get_db)):
    pages = db.query(WikiPageModel).order_by(WikiPageModel.sort_order).all()
    return [{"id": p.id, "slug": p.slug, "title": p.title, "published": p.published, "sort_order": p.sort_order} for p in pages]


@app.post("/admin/wiki", dependencies=[Depends(get_current_admin)])
def create_wiki_page(payload: dict, db: Session = Depends(get_db)):
    slug = payload.get("slug", "").strip()
    title = payload.get("title", "").strip()
    body = payload.get("body", "")
    if not slug or not title:
        raise HTTPException(status_code=400, detail="slug and title required")
    if db.query(WikiPageModel).filter(WikiPageModel.slug == slug).first():
        raise HTTPException(status_code=409, detail="Slug exists")
    page = WikiPageModel(slug=slug, title=title, body=body, sort_order=payload.get("sort_order", 0))
    db.add(page)
    db.commit()
    return {"ok": True, "id": page.id}


@app.put("/admin/wiki/{page_id}", dependencies=[Depends(get_current_admin)])
def update_wiki_page(page_id: int, payload: dict, db: Session = Depends(get_db)):
    page = db.query(WikiPageModel).filter(WikiPageModel.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404)
    for field in ["title", "slug", "body", "published", "sort_order"]:
        if field in payload:
            setattr(page, field, payload[field])
    page.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@app.delete("/admin/wiki/{page_id}", dependencies=[Depends(get_current_admin)])
def delete_wiki_page(page_id: int, db: Session = Depends(get_db)):
    page = db.query(WikiPageModel).filter(WikiPageModel.id == page_id).first()
    if page:
        db.delete(page)
        db.commit()
    return {"ok": True}


@app.get("/health")
def health():
    return {"status": "ok"}
