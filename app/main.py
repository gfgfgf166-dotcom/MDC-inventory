import os
import shutil
from fastapi import FastAPI, Request, Form, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ------------------------
# Database setup
# ------------------------
PGUSER = os.getenv("PGUSER")
PGPASSWORD = os.getenv("PGPASSWORD")
PGHOST = os.getenv("PGHOST")      # Railway tcp_proxy_domain
PGPORT = os.getenv("PGPORT")      # Railway public port
PGDATABASE = os.getenv("PGDATABASE")

DATABASE_URL = f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ------------------------
# Database model
# ------------------------
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    image_path = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# ------------------------
# FastAPI setup
# ------------------------
app = FastAPI(title="Barcode Inventory App")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ------------------------
# Dependency
# ------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------
# Routes
# ------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add-form", response_class=HTMLResponse)
def add_item_form(
    request: Request,
    barcode: str = Form(...),
    name: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if db_item:
        return templates.TemplateResponse("index.html", {"request": request, "message": "❌ Barcode already exists"})

    image_path = None
    if image:
        file_location = f"app/static/images/{image.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_path = f"/static/images/{image.filename}"

    new_item = Item(barcode=barcode, name=name, image_path=image_path)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return templates.TemplateResponse("index.html", {"request": request, "message": f"✅ Added {name} (Barcode: {barcode})", "image_path": image_path})

@app.post("/search-form", response_class=HTMLResponse)
def search_item_form(
    request: Request,
    barcode: str = Form(...),
    db: Session = Depends(get_db)
):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if not db_item:
        return templates.TemplateResponse("index.html", {"request": request, "message": "❌ Item not found"})
    return templates.TemplateResponse("index.html", {"request": request, "message": f"🔎 Found: {db_item.name} (Barcode: {db_item.barcode})", "image_path": db_item.image_path})
