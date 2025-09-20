import os
import uuid
import boto3
from botocore.client import Config
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
PGHOST = os.getenv("PGHOST")      # Railway public host / TCP proxy
PGPORT = os.getenv("PGPORT")      # Railway public port
PGDATABASE = os.getenv("PGDATABASE")

DATABASE_URL = f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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

# Ensure static/images folder exists
os.makedirs("app/static/images", exist_ok=True)
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


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

# Initialize R2 client
r2_client = boto3.client(
    's3',
    endpoint_url=os.getenv("R2_ENDPOINT"),
    aws_access_key_id=os.getenv("R2_KEY"),
    aws_secret_access_key=os.getenv("R2_SECRET"),
    config=Config(signature_version='s3v4')
)

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
    # Check for duplicate barcode
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if db_item:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": "❌ Barcode already exists"}
        )

    image_url = None
    if image:
        ext = os.path.splitext(image.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type")

        contents = image.file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        # Generate unique filename
        unique_name = f"{uuid.uuid4().hex}{ext}"

        # Upload to R2
        r2_client.put_object(
            Bucket=os.getenv("R2_BUCKET"),
            Key=unique_name,
            Body=contents,
            ContentType=image.content_type,
            ACL="public-read"
        )

        # Public URL
        image_url = f"{os.getenv('R2_ENDPOINT')}/{os.getenv('R2_BUCKET')}/{unique_name}"

    # Add to database
    new_item = Item(barcode=barcode, name=name, image_path=image_url)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "message": f"✅ Added {name} (Barcode: {barcode})",
            "image_path": image_url
        }
    )


@app.post("/search-form", response_class=HTMLResponse)
def search_item_form(
    request: Request,
    barcode: str = Form(...),
    db: Session = Depends(get_db)
):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if not db_item:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "message": "❌ Item not found"}
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "message": f"🔎 Found: {db_item.name} (Barcode: {db_item.barcode})",
            "image_path": db_item.image_path
        }
    )
