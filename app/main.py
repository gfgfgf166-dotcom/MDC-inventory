import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# -------------------
# Database Setup
# -------------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# -------------------
# Models
# -------------------
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    name = Column(String, nullable=True)
    color = Column(String, nullable=True)
    height = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    depth = Column(Float, nullable=True)
    material = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    price = Column(Float, nullable=True)

# Create table if not exists
Base.metadata.create_all(bind=engine)

# -------------------
# FastAPI App
# -------------------
app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------
# Routes
# -------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Display all items
@app.get("/display", response_class=HTMLResponse)
def display_items(request: Request, db: Session = Depends(get_db)):
    items = db.query(Item).all()
    return templates.TemplateResponse("display.html", {"request": request, "items": items})

# Add new item
@app.get("/add-form", response_class=HTMLResponse)
def add_form(request: Request, db: Session = Depends(get_db)):
    max_id = db.query(Item.id).order_by(Item.id.desc()).first()
    next_id = (max_id[0] + 1) if max_id else 1
    categories = ["Electronics", "Furniture", "Clothing", "Other"]  # example options
    return templates.TemplateResponse("add.html", {"request": request, "next_id": next_id, "categories": categories})

@app.post("/add-form", response_class=HTMLResponse)
def add_item(
    request: Request,
    id: int = Form(...),
    category: str = Form(...),
    name: str = Form(None),
    color: str = Form(None),
    height: float = Form(None),
    width: float = Form(None),
    depth: float = Form(None),
    material: str = Form(None),
    cost: float = Form(None),
    price: float = Form(None),
    db: Session = Depends(get_db),
):
    new_item = Item(
        id=id,
        category=category,
        name=name,
        color=color,
        height=height,
        width=width,
        depth=depth,
        material=material,
        cost=cost,
        price=price,
    )
    db.add(new_item)
    db.commit()
    return RedirectResponse(url="/display", status_code=303)

# Remove/Edit page – step 1: enter ID
@app.get("/remove-edit", response_class=HTMLResponse)
def remove_edit_form(request: Request):
    return templates.TemplateResponse("remove_edit.html", {"request": request, "item": None, "step": "input"})

# Remove/Edit page – step 2: show item by ID
@app.post("/remove-edit/find", response_class=HTMLResponse)
def find_item(request: Request, id: int = Form(...), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    categories = ["Electronics", "Furniture", "Clothing", "Other"]
    return templates.TemplateResponse("remove_edit.html", {"request": request, "item": item, "categories": categories, "step": "edit"})

# Update item
@app.post("/remove-edit/update", response_class=HTMLResponse)
def update_item(
    request: Request,
    id: int = Form(...),
    category: str = Form(...),
    name: str = Form(None),
    color: str = Form(None),
    height: float = Form(None),
    width: float = Form(None),
    depth: float = Form(None),
    material: str = Form(None),
    cost: float = Form(None),
    price: float = Form(None),
    db: Session = Depends(get_db),
):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.category = category
    item.name = name
    item.color = color
    item.height = height
    item.width = width
    item.depth = depth
    item.material = material
    item.cost = cost
    item.price = price

    db.commit()
    return RedirectResponse(url="/display", status_code=303)

# Delete item
@app.post("/remove-edit/delete", response_class=HTMLResponse)
def delete_item(request: Request, id: int = Form(...), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/display", status_code=303)
