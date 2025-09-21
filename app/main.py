import os
import logging
from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import boto3
from botocore.client import Config
import uvicorn

logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, nullable=True)
    name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# R2 setup
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

# Routes
@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    db = SessionLocal()
    items = db.query(Item).all()
    db.close()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.post("/add-form", response_class=HTMLResponse)
async def add_item_form(
    request: Request,
    barcode: str = Form(None),
    name: str = Form(None),
    image: UploadFile = File(None)
):
    db = SessionLocal()
    image_url = None

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
            logging.info(f"Uploaded {image.filename} to R2 successfully.")
        except Exception as e:
            logging.error(f"R2 upload failed: {e}")
            items = db.query(Item).all()
            db.close()
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "items": items, "message": f"Image upload failed: {e}"}
            )

    try:
        new_item = Item(
            barcode=barcode if barcode else "N/A",
            name=name if name else "Unnamed Item",
            image_url=image_url
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        logging.info(f"Added item {new_item.name} to database.")
    except Exception as e:
        logging.error(f"Database insert failed: {e}")
        db.rollback()
        items = db.query(Item).all()
        db.close()
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "items": items, "message": f"Database error: {e}"}
        )

    items = db.query(Item).all()
    db.close()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "items": items, "message": "Item added successfully!"}
    )

# Railway dynamic port
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
