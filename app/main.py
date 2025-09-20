import os
from typing import Optional

from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import boto3
from botocore.client import Config
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------
# Database setup (SQLite example, replace with PostgreSQL if needed)
# ---------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, nullable=True)
    name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# ---------------------------
# FastAPI setup
# ---------------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# ---------------------------
# Cloudflare R2 setup
# ---------------------------
r2_endpoint = os.getenv("R2_ENDPOINT")
r2_bucket = os.getenv("R2_BUCKET")
r2_token = os.getenv("R2_TOKEN")

r2_client = boto3.client(
    's3',
    endpoint_url=r2_endpoint,
    aws_access_key_id="",
    aws_secret_access_key=r2_token,
    config=Config(signature_version='s3v4')
)

# ---------------------------
# Routes
# ---------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    db = SessionLocal()
    items = db.query(Item).all()
    db.close()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.post("/add-form", response_class=HTMLResponse)
async def add_item_form(
    request: Request,
    barcode: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    db = SessionLocal()
    image_url = None

    # Upload image if provided
    if image:
        contents = await image.read()
        try:
            r2_client.put_object(
                Bucket=r2_bucket,
                Key=image.filename,
                Body=contents,
                ContentType=image.content_type
            )
            image_url = f"{r2_endpoint}/{r2_bucket}/{image.filename}"
        except Exception as e:
            db.close()
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "message": f"Error uploading image: {e}"
                }
            )

    # Add new item to database
    new_item = Item(
        barcode=barcode if barcode else "N/A",
        name=name if name else "Unnamed Item",
        image_url=image_url
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    db.close()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "message": "Item added successfully!",
            "image_path": image_url
        }
    )

# ---------------------------
# Run with Railway / locally
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
