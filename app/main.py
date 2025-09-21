# app/main.py
import os
from fastapi import FastAPI, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import boto3
from botocore.exceptions import NoCredentialsError

# -----------------------------
# Database setup
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set!")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# -----------------------------
# Cloudflare R2 setup
# -----------------------------
R2_ENDPOINT = os.environ.get("R2_ENDPOINT")
R2_BUCKET = os.environ.get("R2_BUCKET")
R2_TOKEN = os.environ.get("R2_TOKEN")

s3_client = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_TOKEN,
    aws_secret_access_key=R2_TOKEN,
)

# -----------------------------
# FastAPI app setup
# -----------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# -----------------------------
# Routes
# -----------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    session = SessionLocal()
    items = session.query(Item).all()
    session.close()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})

@app.post("/add-form")
async def add_form(
    name: str = Form(None),
    description: str = Form(None),
    image: UploadFile = File(None),
):
    session = SessionLocal()
    image_url = None

    if image:
        try:
            s3_client.upload_fileobj(image.file, R2_BUCKET, image.filename)
            image_url = f"{R2_ENDPOINT}/{R2_BUCKET}/{image.filename}"
        except NoCredentialsError:
            return {"error": "Invalid R2 credentials"}

    new_item = Item(name=name, description=description, image_url=image_url)
    session.add(new_item)
    session.commit()
    session.close()

    return RedirectResponse(url="/", status_code=303)
