import os
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, select
from sqlalchemy.orm import sessionmaker

# -----------------------------
# Database Setup
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set!")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
metadata = MetaData()

# Define table with all optional fields
items_table = Table(
    "items",
    metadata,
    Column("id", Integer, primary_key=True, nullable=True),
    Column("barcode", String, nullable=True),
    Column("name", String, nullable=True),
    Column("image_url", String, nullable=True),
)

# Create table if not exists
metadata.create_all(engine)

# -----------------------------
# FastAPI Setup
# -----------------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------------
# Routes
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def read_form(request: Request):
    """Serve the HTML form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/add-form")
async def add_item(
    request: Request,
    id: int | None = Form(None),
    barcode: str | None = Form(None),
    name: str | None = Form(None),
    image_url: str | None = Form(None),
):
    """Insert an item into the DB with all fields optional"""
    db = SessionLocal()
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
    """Display all items in the DB"""
    db = SessionLocal()
    try:
        stmt = select(items_table)
        results = db.execute(stmt).fetchall()
    finally:
        db.close()

    return templates.TemplateResponse("list.html", {"request": request, "items": results})
