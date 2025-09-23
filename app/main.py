import os
import uuid
import io
import mimetypes
import boto3
from fastapi import FastAPI, Request, Form, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load env vars
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_ENDPOINT = os.getenv("R2_ENDPOINT")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, nullable=True)
    name = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# FastAPI setup
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# R2 client
s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
)

# Home page
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Add-form route
@app.post("/add-form")
async def add_item(
    request: Request,
    background_tasks: BackgroundTasks,
    id: int = Form(None),
    barcode: str = Form(None),
    name: str = Form(None),
    image: UploadFile = File(None)
):
    db = SessionLocal()
    image_url = None

    if image:
        ext = image.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        content_type = mimetypes.guess_type(image.filename)[0] or "application/octet-stream"

        # Read file into memory immediately
        file_bytes = await image.read()

        # Upload asynchronously
        background_tasks.add_task(
            lambda b=file_bytes: s3_client.upload_fileobj(
                io.BytesIO(b),
                R2_BUCKET,
                filename,
                ExtraArgs={"ACL": "public-read", "ContentType": content_type}
            )
        )

        image_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{filename}"

    new_item = Item(id=id, barcode=barcode, name=name, image_url=image_url)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    db.close()

    return templates.TemplateResponse("index.html", {"request": request, "message": "Item added!"})
