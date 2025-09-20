import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session


# -------------------------------------------------------------------
# Database models
# -------------------------------------------------------------------
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)


# Create tables if they don't exist
Base.metadata.create_all(bind=engine)


# -------------------------------------------------------------------
# Pydantic schemas
# -------------------------------------------------------------------
class ItemCreate(BaseModel):
    barcode: str
    name: str


class ItemResponse(BaseModel):
    id: int
    barcode: str
    name: str

    class Config:
        orm_mode = True


# -------------------------------------------------------------------
# Dependency
# -------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# -------------------------------------------------------------------
# FastAPI app
# -------------------------------------------------------------------
app = FastAPI(title="Barcode Inventory API")


@app.post("/add", response_model=ItemResponse)
def add_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.barcode == item.barcode).first()
    if db_item:
        raise HTTPException(status_code=400, detail="Barcode already exists")

    new_item = Item(barcode=item.barcode, name=item.name)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/search/{barcode}", response_model=ItemResponse)
def search_item(barcode: str, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.barcode == barcode).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item
