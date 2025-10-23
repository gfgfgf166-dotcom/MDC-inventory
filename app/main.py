import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import barcode
from barcode.writer import ImageWriter

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
    weight = Column(Float, nullable=True)
    material = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    price = Column(Float, nullable=True)

# Create table if not exists
Base.metadata.create_all(bind=engine)

# -------------------
# FastAPI App
# -------------------
app = FastAPI()

# Static folders
os.makedirs("app/static/barcodes", exist_ok=True)
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
# Helper – Generate barcode if not exists
# -------------------
def generate_barcode(item_id: int):
    # Always generate into the same folder served by FastAPI
    barcode_dir = os.path.join("app", "static", "barcodes")
    os.makedirs(barcode_dir, exist_ok=True)

    filename = f"barcode_{item_id}.png"
    filepath = os.path.join(barcode_dir, filename)

    # Only generate if missing
    if not os.path.exists(filepath):
        code = barcode.get("code128", str(item_id), writer=ImageWriter())
        # python-barcode automatically appends .png when saving, so strip it before calling save()
        code.save(filepath[:-4])

    # Return relative path used by templates
    return f"/static/barcodes/{filename}"


# -------------------
# Routes
# -------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "item": None, "error": None})

# Search item by ID
@app.post("/search", response_class=HTMLResponse)
def search_item(request: Request, id: int = Form(...), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "item": None, "error": f"No item found with ID {id}."},
        )
    barcode_path = generate_barcode(item.id)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "item": item, "error": None, "barcode_path": barcode_path},
    )

@app.get("/display", response_class=HTMLResponse)
def display_items(request: Request, db: Session = Depends(get_db)):
    try:
        items = db.query(Item).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    item_data = []
    for i in items:
        # Generate barcode if not exists
        barcode_filename = f"barcode_{i.id}.png"
        barcode_path = os.path.join("static", "barcodes", barcode_filename)
        if not os.path.exists(barcode_path):
            generate_barcode(i.id)
        item_data.append({
            "id": i.id,
            "category": i.category,
            "name": i.name,
            "color": i.color,
            "height": i.height,
            "width": i.width,
            "depth": i.depth,
            "weight": i.weight
            "material": i.material,
            "cost": i.cost,
            "price": i.price,
            "barcode_path": f"barcodes/{barcode_filename}"
        })

    return templates.TemplateResponse("display.html", {"request": request, "items": item_data})


# Add new item
@app.api_route("/add", methods=["GET", "POST"], response_class=HTMLResponse)
async def add_item(request: Request, db: Session = Depends(get_db)):
    if request.method == "POST":
        form = await request.form()

        def to_float(value):
            try:
                return float(value) if value not in (None, "", "None") else None
            except ValueError:
                return None

        def to_int(value):
            try:
                return int(value) if value not in (None, "", "None") else None
            except ValueError:
                return None

        id_val = to_int(form.get("id"))
        category = form.get("category")
        name = form.get("name")
        color = form.get("color")
        height = to_float(form.get("height"))
        width = to_float(form.get("width"))
        depth = to_float(form.get("depth"))
        weight = to_float(form.get("weight"))
        material = form.get("material")
        cost = to_float(form.get("cost"))
        price = to_float(form.get("price"))

        if not category:
            raise HTTPException(status_code=400, detail="Category is required")

        new_item = Item(
            id=id_val,
            category=category,
            name=name,
            color=color,
            height=height,
            width=width,
            depth=depth,
            weight=weight,
            material=material,
            cost=cost,
            price=price,
        )

        db.add(new_item)
        db.commit()

        # Generate barcode
        generate_barcode(new_item.id)
        return RedirectResponse(url="/display", status_code=303)

    max_id = db.query(Item.id).order_by(Item.id.desc()).first()
    next_id = (max_id[0] + 1) if max_id else 1
    categories = ["Art", "Vessels", "Textiles", "Tableware", "Holiday", "Misc."]
    return templates.TemplateResponse("add.html", {"request": request, "next_id": next_id, "categories": categories})
# Remove/Edit page
@app.get("/remove-edit", response_class=HTMLResponse)
def remove_edit_form(request: Request):
    return templates.TemplateResponse("remove_edit.html", {"request": request, "item": None, "step": "input"})

@app.post("/remove-edit/find", response_class=HTMLResponse)
def find_item(request: Request, id: int = Form(...), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    categories = ["Art", "Vessels", "Textiles", "Tableware", "Holiday", "Misc."]
    return templates.TemplateResponse("remove_edit.html", {"request": request, "item": item, "categories": categories, "step": "edit"})

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
    weight: float = Form(None),
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
    item.weight = weight
    item.material = material
    item.cost = cost
    item.price = price

    db.commit()
    return RedirectResponse(url="/display", status_code=303)

@app.post("/remove-edit/delete", response_class=HTMLResponse)
def delete_item(request: Request, id: int = Form(...), db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
    return RedirectResponse(url="/display", status_code=303)