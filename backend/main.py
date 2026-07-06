import os
import httpx
import asyncio
import uuid
import shutil
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path
from html.parser import HTMLParser

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ironyLabs2024!")
SECRET_KEY     = os.getenv("SECRET_KEY", "supersecretkey_change_me")
ALGORITHM      = "HS256"
TOKEN_EXPIRE   = 60 * 24
DB_PATH = os.getenv("DB_PATH", "/app/data/links.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", "/app/data/uploads"))
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml", "image/x-icon"}
STATIC_DIR = os.getenv("STATIC_DIR", "")  # Empty = not standalone mode

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CategoryModel(Base):
    __tablename__ = "categories"
    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String(80), unique=True, nullable=False)
    color    = Column(String(7), default="")
    icon_url = Column(Text, default="")


class SettingModel(Base):
    __tablename__ = "settings"
    key   = Column(String(80), primary_key=True)
    value = Column(Text, default="")


class LinkModel(Base):
    __tablename__ = "links"
    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(120), nullable=False)
    url         = Column(Text, nullable=False)
    category    = Column(String(80), default="General")
    parent_category = Column(String(80), default="")
    tags        = Column(Text, default="")
    icon        = Column(String(80), default="🔗")
    favicon_url = Column(Text, default="")
    description = Column(String(240), default="")
    notes       = Column(Text, default="")
    active      = Column(Boolean, default=True)
    featured    = Column(Boolean, default=False)
    pinned      = Column(Boolean, default=False)
    sort_order  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)
    click_count = Column(Integer, default=0)
    upvotes     = Column(Integer, default=0)
    last_health = Column(String(20), default="")
    health_at   = Column(DateTime, nullable=True)
    private     = Column(Boolean, default=False)
    read_status = Column(String(20), default="none")
    dead_count  = Column(Integer, default=0)
    wayback_url = Column(Text, default="")
    og_image    = Column(Text, default="")
    og_title    = Column(Text, default="")
    expires_at  = Column(DateTime, nullable=True)


class AuditLogModel(Base):
    __tablename__ = "audit_log"
    id         = Column(Integer, primary_key=True, index=True)
    action     = Column(String(40), nullable=False)
    target     = Column(Text, default="")
    details    = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class CommentModel(Base):
    __tablename__ = "comments"
    id         = Column(Integer, primary_key=True, index=True)
    link_id    = Column(Integer, nullable=False)
    author     = Column(String(60), default="Anonymous")
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ViewerAccountModel(Base):
    __tablename__ = "viewer_accounts"
    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(60), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    active     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiKeyModel(Base):
    __tablename__ = "api_keys"
    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(120), nullable=False)
    key        = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    active     = Column(Boolean, default=True)


class ClickLogModel(Base):
    __tablename__ = "click_log"
    id         = Column(Integer, primary_key=True, index=True)
    link_id    = Column(Integer, nullable=False)
    referrer   = Column(Text, default="")
    country    = Column(String(4), default="")
    clicked_at = Column(DateTime, default=datetime.utcnow)


class CollectionModel(Base):
    __tablename__ = "collections"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(120), nullable=False)
    slug        = Column(String(120), unique=True, nullable=False)
    description = Column(Text, default="")
    created_at  = Column(DateTime, default=datetime.utcnow)


class CollectionLinkModel(Base):
    __tablename__ = "collection_links"
    id            = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, nullable=False)
    link_id       = Column(Integer, nullable=False)
    sort_order    = Column(Integer, default=0)


class ShareModel(Base):
    __tablename__ = "shares"
    id         = Column(Integer, primary_key=True, index=True)
    token      = Column(String(64), unique=True, nullable=False)
    name       = Column(String(120), default="")
    share_type = Column(String(20), default="all")  # all, category, collection
    target     = Column(String(120), default="")    # category name or collection slug
    created_at = Column(DateTime, default=datetime.utcnow)


class FriendModel(Base):
    __tablename__ = "friends"
    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(120), nullable=False)
    instance_url = Column(Text, nullable=False)     # e.g. https://friend.com
    share_token  = Column(String(64), default="")   # token for their /api/shared/{token}
    created_at   = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

with engine.connect() as conn:
    from sqlalchemy import text, inspect
    inspector = inspect(engine)
    if 'links' in inspector.get_table_names():
        existing_cols = {c['name'] for c in inspector.get_columns('links')}
        migrations = {
            'click_count': "ALTER TABLE links ADD COLUMN click_count INTEGER DEFAULT 0",
            'last_health': "ALTER TABLE links ADD COLUMN last_health VARCHAR(20) DEFAULT ''",
            'health_at': "ALTER TABLE links ADD COLUMN health_at DATETIME",
            'tags': "ALTER TABLE links ADD COLUMN tags TEXT DEFAULT ''",
            'favicon_url': "ALTER TABLE links ADD COLUMN favicon_url TEXT DEFAULT ''",
            'notes': "ALTER TABLE links ADD COLUMN notes TEXT DEFAULT ''",
            'featured': "ALTER TABLE links ADD COLUMN featured BOOLEAN DEFAULT 0",
            'private': "ALTER TABLE links ADD COLUMN private BOOLEAN DEFAULT 0",
            'read_status': "ALTER TABLE links ADD COLUMN read_status VARCHAR(20) DEFAULT 'none'",
            'dead_count': "ALTER TABLE links ADD COLUMN dead_count INTEGER DEFAULT 0",
            'pinned': "ALTER TABLE links ADD COLUMN pinned BOOLEAN DEFAULT 0",
            'wayback_url': "ALTER TABLE links ADD COLUMN wayback_url TEXT DEFAULT ''",
            'upvotes': "ALTER TABLE links ADD COLUMN upvotes INTEGER DEFAULT 0",
            'og_image': "ALTER TABLE links ADD COLUMN og_image TEXT DEFAULT ''",
            'og_title': "ALTER TABLE links ADD COLUMN og_title TEXT DEFAULT ''",
            'expires_at': "ALTER TABLE links ADD COLUMN expires_at DATETIME",
            'parent_category': "ALTER TABLE links ADD COLUMN parent_category VARCHAR(80) DEFAULT ''",
        }
        for col, sql in migrations.items():
            if col not in existing_cols:
                conn.execute(text(sql))
                conn.commit()
    if 'categories' in inspector.get_table_names():
        cat_cols = {c['name'] for c in inspector.get_columns('categories')}
        if 'icon_url' not in cat_cols:
            conn.execute(text("ALTER TABLE categories ADD COLUMN icon_url TEXT DEFAULT ''"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
HASHED_ADMIN_PW = pwd_ctx.hash(ADMIN_PASSWORD)


def verify_password(plain: str) -> bool:
    return pwd_ctx.verify(plain, HASHED_ADMIN_PW)


def create_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_admin(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return "admin"


class LinkCreate(BaseModel):
    title: str
    url: str
    category: str = "General"
    tags: str = ""
    icon: str = "🔗"
    description: str = ""
    notes: str = ""
    active: bool = True
    featured: bool = False
    pinned: bool = False
    sort_order: int = 0
    private: bool = False
    read_status: str = "none"


class LinkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    featured: Optional[bool] = None
    pinned: Optional[bool] = None
    sort_order: Optional[int] = None
    private: Optional[bool] = None
    read_status: Optional[str] = None


class LinkOut(BaseModel):
    id: int
    title: str
    url: str
    category: str
    tags: str = ""
    icon: str
    favicon_url: str = ""
    description: str
    notes: str = ""
    active: bool
    featured: bool = False
    pinned: bool = False
    sort_order: int
    click_count: int = 0
    upvotes: int = 0
    created_at: Optional[datetime] = None
    last_health: str = ""
    health_at: Optional[datetime] = None
    private: bool = False
    read_status: str = "none"
    dead_count: int = 0
    wayback_url: str = ""
    og_image: str = ""
    og_title: str = ""
    expires_at: Optional[datetime] = None
    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: int
    name: str
    color: str
    icon_url: str = ""
    class Config:
        from_attributes = True


class CategoryUpdate(BaseModel):
    color: Optional[str] = None
    icon_url: Optional[str] = None


class ReorderItem(BaseModel):
    id: int
    sort_order: int


class Token(BaseModel):
    access_token: str
    token_type: str


class CollectionCreate(BaseModel):
    name: str
    slug: str
    description: str = ""


class CollectionOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str = ""
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


app = FastAPI(title="Memex API", root_path="/api")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


def _xml_escape(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


@app.get("/links", response_model=List[LinkOut])
def get_links(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return db.query(LinkModel).filter(
        LinkModel.active == True,
        LinkModel.private != True,
        (LinkModel.expires_at == None) | (LinkModel.expires_at > now)
    ).order_by(LinkModel.pinned.desc(), LinkModel.sort_order, LinkModel.title).all()


@app.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    rows = db.query(LinkModel.category).filter(LinkModel.active == True).distinct().all()
    cat_names = sorted({r[0] for r in rows})
    custom = {c.name: {"color": c.color, "icon_url": c.icon_url or ""} for c in db.query(CategoryModel).all()}
    return [{"name": n, "color": custom.get(n, {}).get("color", ""), "icon_url": custom.get(n, {}).get("icon_url", "")} for n in cat_names]


@app.post("/links/{link_id}/click")
def track_click(link_id: int, request: Request, db: Session = Depends(get_db), referrer: str = ""):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    link.click_count = (link.click_count or 0) + 1
    # Log with referrer and IP-based country (stored as IP for now)
    ip = request.client.host if request.client else ""
    db.add(ClickLogModel(link_id=link_id, referrer=referrer, country=ip[:4]))
    db.commit()
    return {"ok": True, "click_count": link.click_count}


@app.get("/reading-queue", response_model=List[LinkOut])
def get_reading_queue(db: Session = Depends(get_db)):
    return db.query(LinkModel).filter(LinkModel.active == True).filter(LinkModel.private != True).filter(LinkModel.read_status.in_(["to-read", "reading"])).order_by(LinkModel.sort_order, LinkModel.title).all()


@app.get("/rss")
def get_rss_feed(db: Session = Depends(get_db)):
    links = db.query(LinkModel).filter(LinkModel.active == True).filter(LinkModel.private != True).order_by(LinkModel.created_at.desc()).limit(50).all()
    setting = db.query(SettingModel).filter(SettingModel.key == "site_name").first()
    site_name = setting.value if setting else "Memex"
    entries = ""
    for l in links:
        created = l.created_at.isoformat() + "Z" if l.created_at else ""
        entries += f'  <entry><title>{_xml_escape(l.title)}</title><link href="{_xml_escape(l.url)}"/><id>{_xml_escape(l.url)}</id><updated>{created}</updated><summary>{_xml_escape(l.description)}</summary></entry>\n'
    xml = f'<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom">\n  <title>{_xml_escape(site_name)}</title>\n  <updated>{datetime.utcnow().isoformat()}Z</updated>\n  <id>urn:ironyLabs:links</id>\n{entries}</feed>'
    return Response(content=xml, media_type="application/atom+xml")


@app.get("/settings/header")
def get_site_header(db: Session = Depends(get_db)):
    keys = ["site_name", "site_bio", "site_avatar", "site_socials"]
    settings = db.query(SettingModel).filter(SettingModel.key.in_(keys)).all()
    result = {k: "" for k in keys}
    for s in settings:
        result[s.key] = s.value
    return result


@app.get("/settings/theme")
def get_theme(db: Session = Depends(get_db)):
    setting = db.query(SettingModel).filter(SettingModel.key == "theme").first()
    theme_id = setting.value if setting else "dark-orange"
    from_themes = {"dark-orange":{"name":"Dark Orange","bg":"#0a0a0a","accent":"#FF7A29","accentLight":"#FFA35C","text":"#ffffff","glowColor":"rgba(255,122,41,0.12)"},"cyberpunk-blue":{"name":"Cyberpunk Blue","bg":"#0a0a1a","accent":"#00d4ff","accentLight":"#66e5ff","text":"#ffffff","glowColor":"rgba(0,212,255,0.12)"},"minimal-green":{"name":"Minimal Green","bg":"#0a1a0a","accent":"#34d399","accentLight":"#6ee7b7","text":"#ffffff","glowColor":"rgba(52,211,153,0.12)"},"purple-haze":{"name":"Purple Haze","bg":"#0f0a1a","accent":"#a78bfa","accentLight":"#c4b5fd","text":"#ffffff","glowColor":"rgba(167,139,250,0.12)"},"rose-gold":{"name":"Rose Gold","bg":"#1a0a0f","accent":"#f472b6","accentLight":"#f9a8d4","text":"#ffffff","glowColor":"rgba(244,114,182,0.12)"}}
    return {"current": theme_id, "theme": from_themes.get(theme_id, from_themes["dark-orange"]), "available": from_themes}


@app.get("/collections", response_model=List[CollectionOut])
def get_collections(db: Session = Depends(get_db)):
    return db.query(CollectionModel).order_by(CollectionModel.name).all()


@app.get("/collections/{slug}")
def get_collection_by_slug(slug: str, db: Session = Depends(get_db)):
    col = db.query(CollectionModel).filter(CollectionModel.slug == slug).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    cl_rows = db.query(CollectionLinkModel).filter(CollectionLinkModel.collection_id == col.id).order_by(CollectionLinkModel.sort_order).all()
    link_ids = [r.link_id for r in cl_rows]
    links = []
    if link_ids:
        all_links = db.query(LinkModel).filter(LinkModel.id.in_(link_ids), LinkModel.active == True, LinkModel.private != True).all()
        link_map = {l.id: l for l in all_links}
        links = [link_map[lid] for lid in link_ids if lid in link_map]
    return {"id": col.id, "name": col.name, "slug": col.slug, "description": col.description, "links": [LinkOut.model_validate(l) for l in links]}


@app.get("/tags")
def get_tags(db: Session = Depends(get_db)):
    links = db.query(LinkModel.tags).filter(LinkModel.active == True).all()
    all_tags = set()
    for (tags_str,) in links:
        if tags_str:
            for tag in tags_str.split(","):
                t = tag.strip()
                if t:
                    all_tags.add(t)
    return sorted(all_tags)


@app.get("/links/{link_id}/notes")
def get_link_notes(link_id: int, db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"id": link.id, "title": link.title, "notes": link.notes or ""}


@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != "admin" or not verify_password(form_data.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_token({"sub": "admin"}), "token_type": "bearer"}


@app.get("/admin/links", response_model=List[LinkOut], dependencies=[Depends(get_current_admin)])
def admin_list_links(db: Session = Depends(get_db)):
    return db.query(LinkModel).order_by(LinkModel.sort_order, LinkModel.title).all()


@app.post("/admin/links", response_model=LinkOut, dependencies=[Depends(get_current_admin)])
def create_link(payload: LinkCreate, db: Session = Depends(get_db)):
    # Duplicate detection
    existing = db.query(LinkModel).filter(LinkModel.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"URL already exists: '{existing.title}' (id={existing.id})")
    link = LinkModel(**payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    # Webhook notification
    _fire_webhook(db, "link_added", {"title": link.title, "url": link.url, "category": link.category})
    _audit(db, "link_created", link.title, f"url={link.url}")
    return link


@app.put("/admin/links/{link_id}", response_model=LinkOut, dependencies=[Depends(get_current_admin)])
def update_link(link_id: int, payload: LinkUpdate, db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(link, field, value)
    db.commit()
    db.refresh(link)
    return link


@app.delete("/admin/links/{link_id}", dependencies=[Depends(get_current_admin)])
def delete_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    db.delete(link)
    db.commit()
    return {"ok": True}


@app.put("/admin/links/{link_id}/private", dependencies=[Depends(get_current_admin)])
def toggle_private(link_id: int, payload: dict, db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    link.private = payload.get("private", not link.private)
    db.commit()
    return {"ok": True, "private": link.private}


@app.put("/admin/links/{link_id}/read-status", dependencies=[Depends(get_current_admin)])
def set_read_status(link_id: int, payload: dict, db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    new_status = payload.get("read_status", "none")
    if new_status not in ("none", "to-read", "reading", "done"):
        raise HTTPException(status_code=400, detail="Invalid read_status")
    link.read_status = new_status
    db.commit()
    return {"ok": True, "read_status": link.read_status}


@app.get("/admin/stats", dependencies=[Depends(get_current_admin)])
def get_stats(db: Session = Depends(get_db)):
    links = db.query(LinkModel).order_by(LinkModel.click_count.desc()).all()
    total_clicks = sum(l.click_count or 0 for l in links)
    return {"total_clicks": total_clicks, "total_links": len(links), "top_links": [{"id": l.id, "title": l.title, "clicks": l.click_count or 0, "category": l.category} for l in links[:10]]}


@app.put("/admin/settings/header", dependencies=[Depends(get_current_admin)])
def set_site_header(payload: dict, db: Session = Depends(get_db)):
    for key in ["site_name", "site_bio", "site_avatar", "site_socials"]:
        if key in payload:
            s = db.query(SettingModel).filter(SettingModel.key == key).first()
            if s:
                s.value = str(payload[key])
            else:
                db.add(SettingModel(key=key, value=str(payload[key])))
    db.commit()
    return {"ok": True}


@app.put("/admin/settings/theme", dependencies=[Depends(get_current_admin)])
def set_theme(payload: dict, db: Session = Depends(get_db)):
    theme_id = payload.get("theme", "dark-orange")
    s = db.query(SettingModel).filter(SettingModel.key == "theme").first()
    if s:
        s.value = theme_id
    else:
        db.add(SettingModel(key="theme", value=theme_id))
    db.commit()
    return {"ok": True, "theme": theme_id}


@app.get("/admin/settings/auto-archive", dependencies=[Depends(get_current_admin)])
def get_auto_archive(db: Session = Depends(get_db)):
    s = db.query(SettingModel).filter(SettingModel.key == "auto_archive_enabled").first()
    return {"auto_archive_enabled": s.value == "true" if s else False}


@app.put("/admin/settings/auto-archive", dependencies=[Depends(get_current_admin)])
def set_auto_archive(payload: dict, db: Session = Depends(get_db)):
    enabled = "true" if payload.get("enabled") else "false"
    s = db.query(SettingModel).filter(SettingModel.key == "auto_archive_enabled").first()
    if s:
        s.value = enabled
    else:
        db.add(SettingModel(key="auto_archive_enabled", value=enabled))
    db.commit()
    return {"ok": True, "auto_archive_enabled": enabled == "true"}


@app.post("/admin/collections", response_model=CollectionOut, dependencies=[Depends(get_current_admin)])
def create_collection(payload: CollectionCreate, db: Session = Depends(get_db)):
    if db.query(CollectionModel).filter(CollectionModel.slug == payload.slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
    col = CollectionModel(**payload.model_dump())
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


@app.delete("/admin/collections/{col_id}", dependencies=[Depends(get_current_admin)])
def delete_collection(col_id: int, db: Session = Depends(get_db)):
    col = db.query(CollectionModel).filter(CollectionModel.id == col_id).first()
    if not col:
        raise HTTPException(status_code=404, detail="Not found")
    db.query(CollectionLinkModel).filter(CollectionLinkModel.collection_id == col_id).delete()
    db.delete(col)
    db.commit()
    return {"ok": True}


@app.post("/admin/collections/{col_id}/links", dependencies=[Depends(get_current_admin)])
def add_link_to_collection(col_id: int, payload: dict, db: Session = Depends(get_db)):
    link_id = payload.get("link_id")
    if not link_id:
        raise HTTPException(status_code=400, detail="link_id required")
    if db.query(CollectionLinkModel).filter(CollectionLinkModel.collection_id == col_id, CollectionLinkModel.link_id == link_id).first():
        return {"ok": True, "message": "Already in collection"}
    db.add(CollectionLinkModel(collection_id=col_id, link_id=link_id, sort_order=payload.get("sort_order", 0)))
    db.commit()
    return {"ok": True}


@app.delete("/admin/collections/{col_id}/links/{link_id}", dependencies=[Depends(get_current_admin)])
def remove_link_from_collection(col_id: int, link_id: int, db: Session = Depends(get_db)):
    db.query(CollectionLinkModel).filter(CollectionLinkModel.collection_id == col_id, CollectionLinkModel.link_id == link_id).delete()
    db.commit()
    return {"ok": True}


@app.get("/admin/export", dependencies=[Depends(get_current_admin)])
def export_links(db: Session = Depends(get_db)):
    links = db.query(LinkModel).order_by(LinkModel.sort_order, LinkModel.title).all()
    data = [{"title": l.title, "url": l.url, "category": l.category, "tags": l.tags or "", "icon": l.icon, "favicon_url": l.favicon_url or "", "description": l.description, "notes": l.notes or "", "active": l.active, "featured": l.featured or False, "sort_order": l.sort_order} for l in links]
    return JSONResponse(content={"links": data, "exported_at": datetime.utcnow().isoformat()})


@app.post("/admin/import", dependencies=[Depends(get_current_admin)])
async def import_links(file: UploadFile = File(...), db: Session = Depends(get_db)):
    import json
    try:
        content = await file.read()
        payload = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    links_data = payload.get("links", [])
    added = 0
    for item in links_data:
        if not item.get("title") or not item.get("url"):
            continue
        db.add(LinkModel(title=item["title"], url=item["url"], category=item.get("category", "General"), tags=item.get("tags", ""), icon=item.get("icon", "🔗"), favicon_url=item.get("favicon_url", ""), description=item.get("description", ""), notes=item.get("notes", ""), active=item.get("active", True), featured=item.get("featured", False), sort_order=item.get("sort_order", 0)))
        added += 1
    db.commit()
    return {"ok": True, "imported": added}


class _BookmarkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bookmarks = []
        self.current_folder = "General"
        self.current_url = None
        self.current_title = ""
        self.in_a = False
        self.in_h3 = False
        self.folder_name = ""

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "a":
            self.in_a = True
            self.current_title = ""
            self.current_url = dict(attrs).get("href", "")
        elif tag == "h3":
            self.in_h3 = True
            self.folder_name = ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "a" and self.in_a:
            self.in_a = False
            if self.current_url:
                self.bookmarks.append({"title": self.current_title.strip() or self.current_url, "url": self.current_url, "category": self.current_folder})
            self.current_url = None
            self.current_title = ""
        elif tag == "h3" and self.in_h3:
            self.in_h3 = False
            if self.folder_name.strip():
                self.current_folder = self.folder_name.strip()

    def handle_data(self, data):
        if self.in_a:
            self.current_title += data
        elif self.in_h3:
            self.folder_name += data


@app.post("/admin/import/bookmarks", dependencies=[Depends(get_current_admin)])
async def import_bookmarks(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        html_content = content.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file")
    parser = _BookmarkParser()
    parser.feed(html_content)
    added = 0
    for bm in parser.bookmarks:
        if not bm.get("url"):
            continue
        db.add(LinkModel(title=bm["title"][:120], url=bm["url"], category=bm.get("category", "General")[:80], icon="🔗"))
        added += 1
    db.commit()
    return {"ok": True, "imported": added}


@app.put("/admin/reorder", dependencies=[Depends(get_current_admin)])
def reorder_links(items: List[ReorderItem], db: Session = Depends(get_db)):
    for item in items:
        link = db.query(LinkModel).filter(LinkModel.id == item.id).first()
        if link:
            link.sort_order = item.sort_order
    db.commit()
    return {"ok": True, "updated": len(items)}


@app.get("/admin/categories", response_model=List[CategoryOut], dependencies=[Depends(get_current_admin)])
def admin_list_categories(db: Session = Depends(get_db)):
    return db.query(CategoryModel).order_by(CategoryModel.name).all()


@app.put("/admin/categories/{cat_name}", response_model=CategoryOut, dependencies=[Depends(get_current_admin)])
def set_category_color(cat_name: str, payload: CategoryUpdate, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).filter(CategoryModel.name == cat_name).first()
    if cat:
        if payload.color is not None: cat.color = payload.color
        if payload.icon_url is not None: cat.icon_url = payload.icon_url
    else:
        cat = CategoryModel(name=cat_name, color=payload.color or "", icon_url=payload.icon_url or "")
        db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@app.post("/admin/health-check", dependencies=[Depends(get_current_admin)])
async def check_link_health(db: Session = Depends(get_db)):
    links = db.query(LinkModel).filter(LinkModel.active == True).all()
    archive_setting = db.query(SettingModel).filter(SettingModel.key == "auto_archive_enabled").first()
    auto_archive = archive_setting and archive_setting.value == "true"
    results = []
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for link in links:
            try:
                resp = await client.head(link.url)
                if resp.status_code < 400:
                    link.last_health = "ok"
                    link.dead_count = 0
                else:
                    link.last_health = f"error:{resp.status_code}"
                    link.dead_count = (link.dead_count or 0) + 1
            except httpx.TimeoutException:
                link.last_health = "timeout"
                link.dead_count = (link.dead_count or 0) + 1
            except Exception:
                link.last_health = "error"
                link.dead_count = (link.dead_count or 0) + 1
            link.health_at = datetime.utcnow()
            if auto_archive and (link.dead_count or 0) >= 3:
                link.active = False
            results.append({"id": link.id, "title": link.title, "status": link.last_health, "dead_count": link.dead_count or 0})
    db.commit()
    return {"checked": len(results), "results": results}


@app.post("/admin/upload/link-icon/{link_id}", dependencies=[Depends(get_current_admin)])
async def upload_link_icon(link_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type")
    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'png'
    filename = f"link-{link_id}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(UPLOADS_DIR / filename, "wb") as f:
        shutil.copyfileobj(file.file, f)
    link.favicon_url = f"/api/uploads/{filename}"
    db.commit()
    return {"ok": True, "favicon_url": link.favicon_url}


@app.post("/admin/upload/category-icon/{cat_name}", dependencies=[Depends(get_current_admin)])
async def upload_category_icon(cat_name: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type")
    ext = file.filename.rsplit('.', 1)[-1] if '.' in file.filename else 'png'
    safe_name = cat_name.replace(' ', '_').replace('/', '_')[:20]
    filename = f"cat-{safe_name}-{uuid.uuid4().hex[:8]}.{ext}"
    with open(UPLOADS_DIR / filename, "wb") as f:
        shutil.copyfileobj(file.file, f)
    icon_url = f"/api/uploads/{filename}"
    cat = db.query(CategoryModel).filter(CategoryModel.name == cat_name).first()
    if cat:
        cat.icon_url = icon_url
    else:
        cat = CategoryModel(name=cat_name, color="", icon_url=icon_url)
        db.add(cat)
    db.commit()
    return {"ok": True, "icon_url": icon_url}


@app.post("/admin/links/{link_id}/fetch-favicon", dependencies=[Depends(get_current_admin)])
async def fetch_favicon(link_id: int, db: Session = Depends(get_db)):
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    favicon_url = await _get_favicon_url(link.url)
    link.favicon_url = favicon_url or ""
    db.commit()
    return {"ok": True, "favicon_url": link.favicon_url}


@app.post("/admin/fetch-all-favicons", dependencies=[Depends(get_current_admin)])
async def fetch_all_favicons(db: Session = Depends(get_db)):
    links = db.query(LinkModel).filter(LinkModel.favicon_url == "").all()
    updated = 0
    for link in links:
        fav = await _get_favicon_url(link.url)
        if fav:
            link.favicon_url = fav
            updated += 1
    db.commit()
    return {"ok": True, "updated": updated, "total": len(links)}


async def _get_favicon_url(url: str) -> str:
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        google_fav = f"https://www.google.com/s2/favicons?domain={parsed.netloc}&sz=64"
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.head(google_fav)
            if resp.status_code < 400:
                return google_fav
        fallback = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.head(fallback)
            if resp.status_code < 400:
                return fallback
    except Exception:
        pass
    return ""


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Phase 1: Activity Feed ────────────────────────────────────────────────────
@app.get("/activity")
def get_activity(db: Session = Depends(get_db)):
    """Public activity feed — recent link additions and top clicks."""
    recent = db.query(LinkModel).filter(LinkModel.active == True, LinkModel.private != True).order_by(LinkModel.created_at.desc()).limit(10).all()
    return {
        "recent_additions": [{"id": l.id, "title": l.title, "url": l.url, "category": l.category, "icon": l.icon, "created_at": l.created_at.isoformat() if l.created_at else ""} for l in recent],
    }


# ── Phase 1: Public Profile / About ──────────────────────────────────────────
@app.get("/about")
def get_about(db: Session = Depends(get_db)):
    """Public profile page data."""
    keys = ["site_name", "site_bio", "site_avatar", "site_socials", "custom_css"]
    settings = {s.key: s.value for s in db.query(SettingModel).filter(SettingModel.key.in_(keys)).all()}
    total_links = db.query(LinkModel).filter(LinkModel.active == True, LinkModel.private != True).count()
    total_categories = len(set(r[0] for r in db.query(LinkModel.category).filter(LinkModel.active == True).distinct().all()))
    total_clicks = sum(l.click_count or 0 for l in db.query(LinkModel).all())
    return {
        "site_name": settings.get("site_name", "Memex"),
        "site_bio": settings.get("site_bio", ""),
        "site_avatar": settings.get("site_avatar", ""),
        "site_socials": settings.get("site_socials", ""),
        "stats": {"links": total_links, "categories": total_categories, "clicks": total_clicks},
    }


# ── Phase 1: Custom CSS ──────────────────────────────────────────────────────
@app.get("/settings/custom-css")
def get_custom_css(db: Session = Depends(get_db)):
    """Return custom CSS for the public page."""
    row = db.query(SettingModel).filter(SettingModel.key == "custom_css").first()
    return Response(content=row.value if row else "", media_type="text/css")


@app.put("/admin/settings/custom-css", dependencies=[Depends(get_current_admin)])
def set_custom_css(payload: dict, db: Session = Depends(get_db)):
    """Set custom CSS for the public page."""
    css = payload.get("css", "")
    row = db.query(SettingModel).filter(SettingModel.key == "custom_css").first()
    if row:
        row.value = css
    else:
        db.add(SettingModel(key="custom_css", value=css))
    db.commit()
    return {"ok": True}


# ── Phase 1: Archive View ────────────────────────────────────────────────────
@app.get("/admin/archived", response_model=List[LinkOut], dependencies=[Depends(get_current_admin)])
def get_archived_links(db: Session = Depends(get_db)):
    """Return inactive/archived links."""
    return db.query(LinkModel).filter(LinkModel.active == False).order_by(LinkModel.title).all()


# ── Phase 1: Wayback Machine ─────────────────────────────────────────────────
@app.post("/admin/links/{link_id}/wayback", dependencies=[Depends(get_current_admin)])
def set_wayback_url(link_id: int, db: Session = Depends(get_db)):
    """Generate Wayback Machine URL for a dead link."""
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    link.wayback_url = f"https://web.archive.org/web/{link.url}"
    db.commit()
    return {"ok": True, "wayback_url": link.wayback_url}


# ── Phase 1: Webhook Notifications ───────────────────────────────────────────
def _fire_webhook(db: Session, event: str, data: dict):
    """Fire webhook if configured (non-blocking, best-effort)."""
    row = db.query(SettingModel).filter(SettingModel.key == "webhook_url").first()
    if not row or not row.value:
        return
    import threading
    def _send():
        try:
            import urllib.request, json
            payload = json.dumps({"event": event, "data": data}).encode()
            req = urllib.request.Request(row.value, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


@app.put("/admin/settings/webhook", dependencies=[Depends(get_current_admin)])
def set_webhook_url(payload: dict, db: Session = Depends(get_db)):
    """Set webhook URL for notifications (Discord/Slack/custom)."""
    url = payload.get("url", "")
    row = db.query(SettingModel).filter(SettingModel.key == "webhook_url").first()
    if row:
        row.value = url
    else:
        db.add(SettingModel(key="webhook_url", value=url))
    db.commit()
    return {"ok": True, "webhook_url": url}


@app.get("/admin/settings/webhook", dependencies=[Depends(get_current_admin)])
def get_webhook_url(db: Session = Depends(get_db)):
    row = db.query(SettingModel).filter(SettingModel.key == "webhook_url").first()
    return {"webhook_url": row.value if row else ""}


# ── Phase 1: Referrer Stats ──────────────────────────────────────────────────
@app.get("/admin/referrers", dependencies=[Depends(get_current_admin)])
def get_referrers(db: Session = Depends(get_db)):
    """Return top referrers from click log."""
    logs = db.query(ClickLogModel).filter(ClickLogModel.referrer != "").all()
    counts = {}
    for log in logs:
        ref = log.referrer
        counts[ref] = counts.get(ref, 0) + 1
    sorted_refs = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
    return [{"referrer": r, "count": c} for r, c in sorted_refs]


# ── Phase 1: API Keys ────────────────────────────────────────────────────────
@app.post("/admin/api-keys", dependencies=[Depends(get_current_admin)])
def create_api_key(payload: dict, db: Session = Depends(get_db)):
    """Create an API key for programmatic access."""
    import secrets
    name = payload.get("name", "API Key")
    key = secrets.token_urlsafe(32)
    api_key = ApiKeyModel(name=name, key=key)
    db.add(api_key)
    db.commit()
    return {"ok": True, "name": name, "key": key}


@app.get("/admin/api-keys", dependencies=[Depends(get_current_admin)])
def list_api_keys(db: Session = Depends(get_db)):
    keys = db.query(ApiKeyModel).filter(ApiKeyModel.active == True).all()
    return [{"id": k.id, "name": k.name, "key": k.key[:8] + "...", "created_at": k.created_at.isoformat() if k.created_at else ""} for k in keys]


@app.delete("/admin/api-keys/{key_id}", dependencies=[Depends(get_current_admin)])
def revoke_api_key(key_id: int, db: Session = Depends(get_db)):
    key = db.query(ApiKeyModel).filter(ApiKeyModel.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.active = False
    db.commit()
    return {"ok": True}


# API key auth for programmatic access (alternative to JWT)
@app.post("/api-key/links", response_model=LinkOut)
def create_link_via_api_key(payload: LinkCreate, x_api_key: str = "", db: Session = Depends(get_db)):
    """Create a link using an API key (for scripts/bots)."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    key = db.query(ApiKeyModel).filter(ApiKeyModel.key == x_api_key, ApiKeyModel.active == True).first()
    if not key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # Duplicate check
    existing = db.query(LinkModel).filter(LinkModel.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"URL already exists: '{existing.title}'")
    link = LinkModel(**payload.model_dump())
    db.add(link)
    db.commit()
    db.refresh(link)
    _fire_webhook(db, "link_added", {"title": link.title, "url": link.url, "via": "api_key"})
    return link


# ── Phase 1: Rate Limiting (simple in-memory) ────────────────────────────────
_rate_limits = {}  # ip -> (count, window_start)
RATE_LIMIT_MAX = 60  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting on click endpoint."""
    if "/click" in request.url.path:
        ip = request.client.host if request.client else "unknown"
        now = datetime.utcnow().timestamp()
        if ip in _rate_limits:
            count, window_start = _rate_limits[ip]
            if now - window_start < RATE_LIMIT_WINDOW:
                if count >= RATE_LIMIT_MAX:
                    return JSONResponse(status_code=429, content={"detail": "Rate limited"})
                _rate_limits[ip] = (count + 1, window_start)
            else:
                _rate_limits[ip] = (1, now)
        else:
            _rate_limits[ip] = (1, now)
    response = await call_next(request)
    return response


# ── Phase 2: Upvote/Reactions ─────────────────────────────────────────────────
@app.post("/links/{link_id}/upvote")
def upvote_link(link_id: int, db: Session = Depends(get_db)):
    """Anonymous upvote for a link (public, no auth)."""
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    link.upvotes = (link.upvotes or 0) + 1
    db.commit()
    return {"ok": True, "upvotes": link.upvotes}


# ── Phase 2: Auto-Tagging (fetch meta) ───────────────────────────────────────
@app.post("/admin/links/{link_id}/auto-tag", dependencies=[Depends(get_current_admin)])
async def auto_tag_link(link_id: int, db: Session = Depends(get_db)):
    """Fetch page meta and suggest/apply tags + OG data."""
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(link.url, headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text[:50000]  # limit to first 50KB
            # Extract title
            import re
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
            # Extract meta keywords
            kw_match = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
            # Extract OG image
            og_img_match = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
            # Extract OG title
            og_title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
            # Extract description
            desc_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)

            suggested_tags = []
            if kw_match:
                suggested_tags = [t.strip() for t in kw_match.group(1).split(',')][:5]
            if og_img_match:
                link.og_image = og_img_match.group(1)
            if og_title_match:
                link.og_title = og_title_match.group(1)
            if desc_match and not link.description:
                link.description = desc_match.group(1)[:240]
            if suggested_tags and not link.tags:
                link.tags = ', '.join(suggested_tags)
            db.commit()
            return {"ok": True, "suggested_tags": suggested_tags, "og_image": link.og_image, "og_title": link.og_title, "description": link.description}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/admin/auto-tag-all", dependencies=[Depends(get_current_admin)])
async def auto_tag_all(db: Session = Depends(get_db)):
    """Auto-tag all links that have no tags."""
    links = db.query(LinkModel).filter(LinkModel.tags == "").limit(20).all()
    tagged = 0
    for link in links:
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(link.url, headers={"User-Agent": "Mozilla/5.0"})
                html = resp.text[:30000]
                import re
                kw_match = re.search(r'<meta[^>]+name=["\']keywords["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
                og_img = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', html, re.IGNORECASE)
                if kw_match:
                    link.tags = ', '.join([t.strip() for t in kw_match.group(1).split(',')][:5])
                    tagged += 1
                if og_img:
                    link.og_image = og_img.group(1)
        except Exception:
            pass
    db.commit()
    return {"ok": True, "tagged": tagged, "total": len(links)}


# ── Phase 2: Bulk Actions ─────────────────────────────────────────────────────
@app.post("/admin/bulk-action", dependencies=[Depends(get_current_admin)])
def bulk_action(payload: dict, db: Session = Depends(get_db)):
    """Perform bulk operations on multiple links."""
    ids = payload.get("ids", [])
    action = payload.get("action", "")
    value = payload.get("value", "")

    if not ids or not action:
        raise HTTPException(status_code=400, detail="ids and action required")

    links = db.query(LinkModel).filter(LinkModel.id.in_(ids)).all()
    affected = 0

    for link in links:
        if action == "delete":
            db.delete(link)
        elif action == "set_category":
            link.category = value
        elif action == "set_tags":
            link.tags = value
        elif action == "activate":
            link.active = True
        elif action == "deactivate":
            link.active = False
        elif action == "set_private":
            link.private = True
        elif action == "set_public":
            link.private = False
        elif action == "set_featured":
            link.featured = True
        elif action == "unset_featured":
            link.featured = False
        affected += 1

    db.commit()
    _audit(db, f"bulk_{action}", f"{affected} links", f"ids={ids}")
    return {"ok": True, "affected": affected}


# ── Phase 2: Click Heatmap ────────────────────────────────────────────────────
@app.get("/admin/click-heatmap", dependencies=[Depends(get_current_admin)])
def get_click_heatmap(db: Session = Depends(get_db)):
    """Return click counts by hour of day (0-23)."""
    logs = db.query(ClickLogModel).all()
    hours = [0] * 24
    days = [0] * 7  # Mon=0, Sun=6
    for log in logs:
        if log.clicked_at:
            hours[log.clicked_at.hour] += 1
            days[log.clicked_at.weekday()] += 1
    return {"by_hour": hours, "by_day": days, "total": len(logs)}


# ── Phase 2: Audit Log ────────────────────────────────────────────────────────
def _audit(db: Session, action: str, target: str, details: str = ""):
    """Record an admin action to the audit log."""
    db.add(AuditLogModel(action=action, target=target, details=details))
    db.commit()


@app.get("/admin/audit-log", dependencies=[Depends(get_current_admin)])
def get_audit_log(db: Session = Depends(get_db)):
    """Return the last 100 audit log entries."""
    logs = db.query(AuditLogModel).order_by(AuditLogModel.created_at.desc()).limit(100).all()
    return [{"id": l.id, "action": l.action, "target": l.target, "details": l.details, "created_at": l.created_at.isoformat() if l.created_at else ""} for l in logs]


# ── Phase 2: Link Expiration ──────────────────────────────────────────────────
@app.put("/admin/links/{link_id}/expires", dependencies=[Depends(get_current_admin)])
def set_link_expiration(link_id: int, payload: dict, db: Session = Depends(get_db)):
    """Set expiration date for a link. Pass expires_at as ISO string or null to clear."""
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    expires_str = payload.get("expires_at")
    if expires_str:
        link.expires_at = datetime.fromisoformat(expires_str.replace("Z", ""))
    else:
        link.expires_at = None
    db.commit()
    return {"ok": True, "expires_at": link.expires_at.isoformat() if link.expires_at else None}


# ── Phase 2: Export to Notion/Obsidian (Markdown) ─────────────────────────────
@app.get("/admin/export/markdown", dependencies=[Depends(get_current_admin)])
def export_markdown(db: Session = Depends(get_db)):
    """Export all links as a Markdown document (Obsidian/Notion compatible)."""
    links = db.query(LinkModel).order_by(LinkModel.category, LinkModel.sort_order, LinkModel.title).all()
    md = "# Memex Links Export\n\n"
    md += f"*Exported: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*\n\n"
    current_cat = ""
    for l in links:
        if l.category != current_cat:
            current_cat = l.category
            md += f"\n## {current_cat}\n\n"
        status = ""
        if not l.active:
            status = " *(archived)*"
        elif l.private:
            status = " *(private)*"
        md += f"- [{l.title}]({l.url}){status}\n"
        if l.description:
            md += f"  - {l.description}\n"
        if l.tags:
            md += f"  - Tags: {l.tags}\n"
        if l.notes:
            md += f"  - Notes: {l.notes[:100]}{'...' if len(l.notes) > 100 else ''}\n"
    return Response(content=md, media_type="text/markdown", headers={"Content-Disposition": "attachment; filename=ironylabs-links.md"})


# ── Phase 2: Visitor Theme Preference ─────────────────────────────────────────
@app.get("/settings/visitor-prefs")
def get_visitor_prefs():
    """Return available visitor preferences (dark/light toggle handled client-side)."""
    return {"modes": ["dark", "light"], "default": "dark"}


# ── Phase 4: Multiple Map Layouts ─────────────────────────────────────────────
@app.get("/settings/layout")
def get_layout(db: Session = Depends(get_db)):
    """Return current mind map layout setting."""
    row = db.query(SettingModel).filter(SettingModel.key == "map_layout").first()
    current = row.value if row else "force"
    return {"current": current, "available": ["force", "radial", "tree", "circular"]}


@app.put("/admin/settings/layout", dependencies=[Depends(get_current_admin)])
def set_layout(payload: dict, db: Session = Depends(get_db)):
    """Set mind map layout mode."""
    layout = payload.get("layout", "force")
    valid = ["force", "radial", "tree", "circular"]
    if layout not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid layout. Use: {valid}")
    row = db.query(SettingModel).filter(SettingModel.key == "map_layout").first()
    if row:
        row.value = layout
    else:
        db.add(SettingModel(key="map_layout", value=layout))
    db.commit()
    return {"ok": True, "layout": layout}


# ── Phase 4: Link Thumbnails/Screenshots ──────────────────────────────────────
@app.post("/admin/links/{link_id}/screenshot", dependencies=[Depends(get_current_admin)])
async def capture_screenshot(link_id: int, db: Session = Depends(get_db)):
    """Generate a thumbnail URL for a link using thum.io service."""
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    # Use free thum.io service (no API key needed)
    from urllib.parse import quote
    thumbnail_url = f"https://image.thum.io/get/width/300/crop/200/{quote(link.url)}"
    link.og_image = thumbnail_url
    db.commit()
    return {"ok": True, "thumbnail_url": thumbnail_url}


@app.post("/admin/screenshots-all", dependencies=[Depends(get_current_admin)])
async def capture_all_screenshots(db: Session = Depends(get_db)):
    """Generate thumbnail URLs for all links without an og_image."""
    from urllib.parse import quote
    links = db.query(LinkModel).filter(LinkModel.og_image == "").all()
    updated = 0
    for link in links:
        link.og_image = f"https://image.thum.io/get/width/300/crop/200/{quote(link.url)}"
        updated += 1
    db.commit()
    return {"ok": True, "updated": updated}


# ── Phase 3: Comments ─────────────────────────────────────────────────────────
@app.get("/links/{link_id}/comments")
def get_comments(link_id: int, db: Session = Depends(get_db)):
    """Get comments for a link (public)."""
    comments = db.query(CommentModel).filter(CommentModel.link_id == link_id).order_by(CommentModel.created_at.desc()).limit(50).all()
    return [{"id": c.id, "author": c.author, "text": c.text, "created_at": c.created_at.isoformat() if c.created_at else ""} for c in comments]


@app.post("/links/{link_id}/comments")
def add_comment(link_id: int, payload: dict, db: Session = Depends(get_db)):
    """Add a comment to a link (public, anonymous allowed)."""
    text = payload.get("text", "").strip()
    if not text or len(text) > 500:
        raise HTTPException(status_code=400, detail="Comment text required (max 500 chars)")
    link = db.query(LinkModel).filter(LinkModel.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    # Check if comments are enabled
    setting = db.query(SettingModel).filter(SettingModel.key == "comments_enabled").first()
    if setting and setting.value == "false":
        raise HTTPException(status_code=403, detail="Comments are disabled")
    comment = CommentModel(link_id=link_id, author=payload.get("author", "Anonymous")[:60], text=text)
    db.add(comment)
    db.commit()
    return {"ok": True, "id": comment.id}


@app.delete("/admin/comments/{comment_id}", dependencies=[Depends(get_current_admin)])
def delete_comment(comment_id: int, db: Session = Depends(get_db)):
    """Delete a comment (admin only)."""
    c = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    if c:
        db.delete(c)
        db.commit()
    return {"ok": True}


@app.put("/admin/settings/comments", dependencies=[Depends(get_current_admin)])
def toggle_comments(payload: dict, db: Session = Depends(get_db)):
    enabled = "true" if payload.get("enabled", True) else "false"
    row = db.query(SettingModel).filter(SettingModel.key == "comments_enabled").first()
    if row:
        row.value = enabled
    else:
        db.add(SettingModel(key="comments_enabled", value=enabled))
    db.commit()
    return {"ok": True, "comments_enabled": enabled == "true"}


# ── Phase 3: Nested Categories ────────────────────────────────────────────────
@app.get("/categories/tree")
def get_category_tree(db: Session = Depends(get_db)):
    """Return categories as a tree structure (parent → children)."""
    links = db.query(LinkModel).filter(LinkModel.active == True, LinkModel.private != True).all()
    tree = {}
    for l in links:
        parent = l.parent_category or ""
        cat = l.category
        if parent:
            if parent not in tree:
                tree[parent] = {"name": parent, "children": []}
            if cat not in [c["name"] for c in tree[parent]["children"]]:
                tree[parent]["children"].append({"name": cat, "count": 0})
            for child in tree[parent]["children"]:
                if child["name"] == cat:
                    child["count"] += 1
        else:
            if cat not in tree:
                tree[cat] = {"name": cat, "children": []}
    return list(tree.values())


# ── Phase 3: Raindrop/Pocket Import ──────────────────────────────────────────
@app.post("/admin/import/raindrop", dependencies=[Depends(get_current_admin)])
async def import_raindrop(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import from Raindrop.io JSON export."""
    import json
    try:
        content = await file.read()
        data = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    items = data if isinstance(data, list) else data.get("items", [])
    added = 0
    for item in items:
        url = item.get("link", "") or item.get("url", "")
        title = item.get("title", "") or item.get("excerpt", "")
        if not url:
            continue
        if db.query(LinkModel).filter(LinkModel.url == url).first():
            continue
        cat = "General"
        if item.get("collection", {}).get("title"):
            cat = item["collection"]["title"]
        elif item.get("tags"):
            cat = item["tags"][0] if isinstance(item["tags"], list) else "General"
        db.add(LinkModel(title=title[:120] or url[:120], url=url, category=cat[:80], tags=', '.join(item.get("tags", []))[:200]))
        added += 1
    db.commit()
    return {"ok": True, "imported": added}


@app.post("/admin/import/pocket", dependencies=[Depends(get_current_admin)])
async def import_pocket(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import from Pocket HTML export."""
    try:
        content = await file.read()
        html = content.decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file")
    import re
    links_found = re.findall(r'<a\s+href="([^"]+)"[^>]*>([^<]*)</a>', html, re.IGNORECASE)
    added = 0
    for url, title in links_found:
        if not url.startswith("http"):
            continue
        if db.query(LinkModel).filter(LinkModel.url == url).first():
            continue
        db.add(LinkModel(title=(title or url)[:120], url=url, category="Pocket"))
        added += 1
    db.commit()
    return {"ok": True, "imported": added}


# ── Phase 3: Geographic Stats ─────────────────────────────────────────────────
@app.get("/admin/geo-stats", dependencies=[Depends(get_current_admin)])
def get_geo_stats(db: Session = Depends(get_db)):
    """Return click counts by country code."""
    logs = db.query(ClickLogModel).filter(ClickLogModel.country != "").all()
    counts = {}
    for log in logs:
        counts[log.country] = counts.get(log.country, 0) + 1
    sorted_countries = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:30]
    return [{"country": c, "clicks": n} for c, n in sorted_countries]


# ── Phase 3: Viewer Accounts ─────────────────────────────────────────────────
@app.post("/admin/viewers", dependencies=[Depends(get_current_admin)])
def create_viewer(payload: dict, db: Session = Depends(get_db)):
    """Create an invite-only viewer account."""
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    if db.query(ViewerAccountModel).filter(ViewerAccountModel.username == username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    hashed = pwd_ctx.hash(password)
    viewer = ViewerAccountModel(username=username, password_hash=hashed)
    db.add(viewer)
    db.commit()
    return {"ok": True, "username": username}


@app.get("/admin/viewers", dependencies=[Depends(get_current_admin)])
def list_viewers(db: Session = Depends(get_db)):
    viewers = db.query(ViewerAccountModel).order_by(ViewerAccountModel.username).all()
    return [{"id": v.id, "username": v.username, "active": v.active, "created_at": v.created_at.isoformat() if v.created_at else ""} for v in viewers]


@app.delete("/admin/viewers/{viewer_id}", dependencies=[Depends(get_current_admin)])
def delete_viewer(viewer_id: int, db: Session = Depends(get_db)):
    v = db.query(ViewerAccountModel).filter(ViewerAccountModel.id == viewer_id).first()
    if v:
        db.delete(v)
        db.commit()
    return {"ok": True}


@app.post("/viewer/login")
def viewer_login(payload: dict, db: Session = Depends(get_db)):
    """Login as a viewer (read-only access)."""
    username = payload.get("username", "")
    password = payload.get("password", "")
    viewer = db.query(ViewerAccountModel).filter(ViewerAccountModel.username == username, ViewerAccountModel.active == True).first()
    if not viewer or not pwd_ctx.verify(password, viewer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token({"sub": f"viewer:{username}"})
    return {"access_token": token, "token_type": "bearer", "role": "viewer"}


# ── Phase 3: Two-Factor Auth (TOTP) ──────────────────────────────────────────
@app.get("/admin/settings/totp", dependencies=[Depends(get_current_admin)])
def get_totp_status(db: Session = Depends(get_db)):
    """Check if TOTP is enabled."""
    row = db.query(SettingModel).filter(SettingModel.key == "totp_secret").first()
    return {"totp_enabled": bool(row and row.value)}


@app.post("/admin/settings/totp/setup", dependencies=[Depends(get_current_admin)])
def setup_totp(db: Session = Depends(get_db)):
    """Generate a new TOTP secret. Returns the secret for QR code generation."""
    import secrets, base64
    secret = base64.b32encode(secrets.token_bytes(20)).decode('utf-8').rstrip('=')
    row = db.query(SettingModel).filter(SettingModel.key == "totp_secret").first()
    if row:
        row.value = secret
    else:
        db.add(SettingModel(key="totp_secret", value=secret))
    db.commit()
    uri = f"otpauth://totp/Memex:admin?secret={secret}&issuer=Memex"
    return {"secret": secret, "uri": uri}


@app.post("/admin/settings/totp/disable", dependencies=[Depends(get_current_admin)])
def disable_totp(db: Session = Depends(get_db)):
    """Disable TOTP."""
    row = db.query(SettingModel).filter(SettingModel.key == "totp_secret").first()
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True, "totp_enabled": False}


# ── Phase 3: Link Age vs Clicks ──────────────────────────────────────────────
@app.get("/admin/age-vs-clicks", dependencies=[Depends(get_current_admin)])
def get_age_vs_clicks(db: Session = Depends(get_db)):
    """Return link age (days) vs click count for charting."""
    now = datetime.utcnow()
    links = db.query(LinkModel).filter(LinkModel.created_at != None).all()
    data = []
    for l in links:
        age_days = (now - l.created_at).days if l.created_at else 0
        data.append({"id": l.id, "title": l.title, "age_days": age_days, "clicks": l.click_count or 0})
    return sorted(data, key=lambda x: x["age_days"])


# ── Phase 3: IFTTT/Zapier Webhook Format ──────────────────────────────────────
@app.get("/admin/settings/integrations", dependencies=[Depends(get_current_admin)])
def get_integrations(db: Session = Depends(get_db)):
    """Return integration settings."""
    webhook = db.query(SettingModel).filter(SettingModel.key == "webhook_url").first()
    zapier = db.query(SettingModel).filter(SettingModel.key == "zapier_webhook").first()
    return {
        "webhook_url": webhook.value if webhook else "",
        "zapier_webhook": zapier.value if zapier else "",
    }


@app.put("/admin/settings/integrations", dependencies=[Depends(get_current_admin)])
def set_integrations(payload: dict, db: Session = Depends(get_db)):
    """Set integration webhook URLs."""
    for key in ["webhook_url", "zapier_webhook"]:
        if key in payload:
            row = db.query(SettingModel).filter(SettingModel.key == key).first()
            if row:
                row.value = payload[key]
            else:
                db.add(SettingModel(key=key, value=payload[key]))
    db.commit()
    return {"ok": True}


# ── Sharing ───────────────────────────────────────────────────────────────────
@app.get("/shared/{token}")
def get_shared_links(token: str, db: Session = Depends(get_db)):
    """Public endpoint — returns links scoped by share token (read-only)."""
    share = db.query(ShareModel).filter(ShareModel.token == token).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found or expired")

    # Get site info for the viewer
    site_name_row = db.query(SettingModel).filter(SettingModel.key == "site_name").first()
    site_name = site_name_row.value if site_name_row else "Memex"

    # Scope links based on share type
    query = db.query(LinkModel).filter(LinkModel.active == True).filter(LinkModel.private != True)

    if share.share_type == "category" and share.target:
        query = query.filter(LinkModel.category == share.target)
    elif share.share_type == "collection" and share.target:
        col = db.query(CollectionModel).filter(CollectionModel.slug == share.target).first()
        if col:
            link_ids = [cl.link_id for cl in db.query(CollectionLinkModel).filter(CollectionLinkModel.collection_id == col.id).all()]
            query = query.filter(LinkModel.id.in_(link_ids)) if link_ids else query.filter(LinkModel.id == -1)
        else:
            query = query.filter(LinkModel.id == -1)
    # share_type == "all" returns all active non-private links

    links = query.order_by(LinkModel.sort_order, LinkModel.title).all()

    return {
        "owner": site_name,
        "share_name": share.name,
        "share_type": share.share_type,
        "target": share.target,
        "links": [LinkOut.model_validate(l) for l in links],
    }


@app.post("/admin/shares", dependencies=[Depends(get_current_admin)])
def create_share(payload: dict, db: Session = Depends(get_db)):
    """Create a new share token."""
    import secrets
    token = secrets.token_urlsafe(32)
    share = ShareModel(
        token=token,
        name=payload.get("name", "Shared Links"),
        share_type=payload.get("share_type", "all"),
        target=payload.get("target", ""),
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return {"ok": True, "id": share.id, "token": share.token, "share_type": share.share_type, "target": share.target}


@app.get("/admin/shares", dependencies=[Depends(get_current_admin)])
def list_shares(db: Session = Depends(get_db)):
    """List all share tokens."""
    shares = db.query(ShareModel).order_by(ShareModel.created_at.desc()).all()
    return [{"id": s.id, "token": s.token, "name": s.name, "share_type": s.share_type, "target": s.target, "created_at": s.created_at.isoformat() if s.created_at else ""} for s in shares]


@app.delete("/admin/shares/{share_id}", dependencies=[Depends(get_current_admin)])
def delete_share(share_id: int, db: Session = Depends(get_db)):
    """Revoke a share token."""
    share = db.query(ShareModel).filter(ShareModel.id == share_id).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    db.delete(share)
    db.commit()
    return {"ok": True}


# ── Friends ───────────────────────────────────────────────────────────────────
@app.get("/friends")
def list_friends_public(db: Session = Depends(get_db)):
    """Public — list friend names (for mind map friend nodes)."""
    friends = db.query(FriendModel).order_by(FriendModel.name).all()
    return [{"id": f.id, "name": f.name} for f in friends]


@app.get("/friends/{friend_id}/links")
async def get_friend_links(friend_id: int, db: Session = Depends(get_db)):
    """Fetch links from a friend's instance via their share token (read-only proxy)."""
    friend = db.query(FriendModel).filter(FriendModel.id == friend_id).first()
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")

    share_url = f"{friend.instance_url.rstrip('/')}/api/shared/{friend.share_token}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(share_url)
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(status_code=502, detail=f"Friend's server returned {resp.status_code}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Friend's server timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach friend: {str(e)}")


@app.get("/admin/friends", dependencies=[Depends(get_current_admin)])
def admin_list_friends(db: Session = Depends(get_db)):
    """List all friends with full details."""
    friends = db.query(FriendModel).order_by(FriendModel.name).all()
    return [{"id": f.id, "name": f.name, "instance_url": f.instance_url, "share_token": f.share_token, "created_at": f.created_at.isoformat() if f.created_at else ""} for f in friends]


@app.post("/admin/friends", dependencies=[Depends(get_current_admin)])
def add_friend(payload: dict, db: Session = Depends(get_db)):
    """Add a friend's instance."""
    name = payload.get("name", "").strip()
    instance_url = payload.get("instance_url", "").strip()
    share_token = payload.get("share_token", "").strip()
    if not name or not instance_url:
        raise HTTPException(status_code=400, detail="name and instance_url required")
    friend = FriendModel(name=name, instance_url=instance_url, share_token=share_token)
    db.add(friend)
    db.commit()
    db.refresh(friend)
    return {"ok": True, "id": friend.id, "name": friend.name}


@app.delete("/admin/friends/{friend_id}", dependencies=[Depends(get_current_admin)])
def remove_friend(friend_id: int, db: Session = Depends(get_db)):
    """Remove a friend."""
    friend = db.query(FriendModel).filter(FriendModel.id == friend_id).first()
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found")
    db.delete(friend)
    db.commit()
    return {"ok": True}


# ── Standalone Mode: Serve Frontend Static Files ──────────────────────────────
if STATIC_DIR and Path(STATIC_DIR).exists():
    from fastapi.responses import FileResponse

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{path:path}", include_in_schema=False)
    async def serve_static_catchall(path: str = ""):
        static_path = Path(STATIC_DIR)
        if path and (static_path / path).exists():
            return FileResponse(str(static_path / path))
        if path.startswith("js/") and (static_path / path).exists():
            return FileResponse(str(static_path / path), media_type="application/javascript")
        return FileResponse(str(static_path / "index.html"))
