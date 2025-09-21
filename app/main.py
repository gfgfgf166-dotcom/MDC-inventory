import os
from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, select
from sqlalchemy.orm import sessionmaker
import uuid
import shutil

# -----------------------------
# Database Setup
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set!")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

items_table = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True, nullable=True),
    Column("barcode", String, nullable=True),
    Column("name", String, nullable=True),
    Column("image_url", String, nullable=True),
)

metadata.create_all(engine)

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Serve uploaded images
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------
# Routes
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add-form")
async def add_item(
    request: Request,
    id: int | None = Form(None),
    barcode: str | None = Form(None),
    name: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    db = SessionLocal()
    image_url = None

    # Handle uploaded image
    if image:
        # Generate unique filename
        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Save file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Store URL relative to /static
        image_url = f"/static/uploads/{filename}"

    try:
        insert_stmt = items_table.insert().values(
            id=id,
            barcode=barcode,
            name=name,
            image_url=image_url,
        )
        db.execute(insert_stmt)
        db.commit()
        message = "✅ Item added successfully!"
    except Exception as e:
        db.rollback()
        message = f"❌ Error: {str(e)}"
    finally:
        db.close()

    return templates.TemplateResponse("index.html", {"request": request, "message": message})

@app.get("/list-items", response_class=HTMLResponse)
async def list_items(request: Request):
    db = SessionLocal()
    try:
        stmt = select(items_table)
        results = db.execute(stmt).fetchall()
    finally:
        db.close()

    return templates.TemplateResponse("list.html", {"request": request, "items": results})
