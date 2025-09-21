import os
import uuid
import boto3
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, MetaData, Table, select
from sqlalchemy.orm import sessionmaker

# -----------------------------
# Database setup
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

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
# R2 setup
# -----------------------------
R2_ENDPOINT = os.getenv("R2_ENDPOINT_URL")
R2_BUCKET = os.getenv("R2_BUCKET_NAME")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")

if not all([R2_ENDPOINT, R2_BUCKET, R2_ACCESS_KEY, R2_SECRET_KEY]):
    raise RuntimeError("R2 environment variables not set")

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# -----------------------------
# FastAPI setup
# -----------------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------------
# Routes
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
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

    # Upload image to R2
    if image:
        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        s3_client.upload_fileobj(
            image.file,
            R2_BUCKET,
            filename,
            ExtraArgs={"ACL": "public-read", "ContentType": image.content_type},
        )
        image_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{filename}"

    try:
        db.execute(
            items_table.insert().values(
                id=id,
                barcode=barcode,
                name=name,
                image_url=image_url,
            )
        )
        db.commit()
        message = "✅ Item added successfully!"
    except Exception as e:
        db.rollback()
        message = f"❌ Error: {str(e)}"
    finally:
        db.close()

    return templates.TemplateResponse("index.html", {"request": request, "message": message})
