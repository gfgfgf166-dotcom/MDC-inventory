# app/main.py
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import os
print("DATABASE_URL =", os.getenv("DATABASE_URL"))


# -----------------------------
# DATABASE SETUP
# -----------------------------
DATABASE_URL = os.getenv("DATABASE_URL")  # Make sure this is the public Railway Postgres URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True)
    name = Column(String)
    quantity = Column(Integer)

# Create tables automatically
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# FASTAPI APP
# -----------------------------
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")  # Make sure index.html is here

# Serve HTML form at /
@app.get("/", response_class=HTMLResponse)
def read_form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# POST endpoint to add products
@app.post("/product")
def add_product(
    barcode: str = Form(...),
    name: str = Form(...),
    quantity: int = Form(...),
    db: Session = next(get_db())
):
    existing = db.query(Product).filter(Product.barcode == barcode).first()
    if existing:
        raise HTTPException(status_code=400, detail="Barcode already exists")
    new_item = Product(barcode=barcode, name=name, quantity=quantity)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Product added successfully", "product": {"barcode": barcode, "name": name, "quantity": quantity}}
    
    try:
    with engine.connect() as conn:
        result = conn.execute("SELECT 1")
        print("Database connection OK:", result.scalar())
except Exception as e:
    print("Database connection failed:", e)
