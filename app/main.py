import os
from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# -------------------------------------------------------------------
# Database setup
# -------------------------------------------------------------------
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGHOST = os.getenv("PGHOST")      # use tcp_proxy_domain from Railway
PGPORT = os.getenv("PGPORT")      # use the public port
PGDATABASE = os.getenv("PGDATABASE")

DATABASE_URL = f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# -------------------------------------------------------------------
# Database models
# -------------------------------------------------------------------
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)


# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


# -------------------------------------------------------------------
# Pydantic schemas
# -------------------------------------------------------------------
class ItemCreate(BaseModel):
    barcode: str
    name: str


class ItemResponse(BaseModel):
    id: int
    barcode: str
    name: str

    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# Dependency
# -------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# FastAPI app + Templates
# -------------------------------------------------------------------
app = FastAPI(title="Barcode Inventory API")

# Serve templates and static files
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------
@app.post("/add", response_model=ItemResponse)
def add_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.barcode == item.barcode).first()
    if db_item:
        raise HTTPException(status_code=400, detail="Barcode already exists")

    new_item = Item(barcode=item.barcode, name=item.name)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/search/{barcode}", response_model=ItemResponse)
def search_item(barcode: str, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item


# -------------------------------------------------------------------
# HTML UI
# -------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/add-form", response_class=HTMLResponse)
def add_item_form(request: Request, barcode: str = Form(...), name: str = Form(...), db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if db_item:
        return templates.TemplateResponse("index.html", {"request": request, "message": "❌ Barcode already exists"})
    new_item = Item(barcode=barcode, name=name)
    db.add(new_item)
    db.commit()
    return templates.TemplateResponse("index.html", {"request": request, "message": f"✅ Added {name} (Barcode: {barcode})"})


@app.post("/search-form", response_class=HTMLResponse)
def search_item_form(request: Request, barcode: str = Form(...), db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if not db_item:
        return templates.TemplateResponse("index.html", {"request": request, "message": "❌ Item not found"})
    return templates.TemplateResponse("index.html", {"request": request, "message": f"🔎 Found: {db_item.name} (Barcode: {db_item.barcode})"})
