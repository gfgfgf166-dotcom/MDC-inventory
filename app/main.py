from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
import os

# --- Database setup ---
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Model ---
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True)
    name = Column(String)
    quantity = Column(Integer)

Base.metadata.create_all(bind=engine)

# --- App ---
app = FastAPI()

# --- Dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Schema ---
class ProductCreate(BaseModel):
    barcode: str
    name: str
    quantity: int

# --- Add product endpoint ---
@app.post("/product")
def add_product(product: ProductCreate, db: Session = Depends(get_db)):
    # check if barcode already exists
    existing = db.query(Product).filter(Product.barcode == product.barcode).first()
    if existing:
        raise HTTPException(status_code=400, detail="Barcode already exists")

    new_item = Product(**product.dict())
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return {"message": "Product added", "product": product.dict()}
