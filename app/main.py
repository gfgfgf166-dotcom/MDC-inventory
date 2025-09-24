from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Mount templates
templates = Jinja2Templates(directory="templates")

# In-memory data table
data = []

# -------------------- Home --------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "data": data})

# -------------------- Display --------------------
@app.get("/display", response_class=HTMLResponse)
async def display_items(request: Request):
    return templates.TemplateResponse("display.html", {"request": request, "data": data})

# -------------------- Add Form (GET) --------------------
@app.get("/add", response_class=HTMLResponse)
async def add_form(request: Request):
    return templates.TemplateResponse("add.html", {"request": request})

# -------------------- Add Item (POST) --------------------
@app.post("/add")
async def add_item(
    request: Request,
    category: str = Form(...),
    name: str = Form(...),
    color: str = Form(None),
    height: float = Form(None),
    width: float = Form(None),
    depth: float = Form(None),
    material: str = Form(None),
    cost: float = Form(None),
    price: float = Form(None),
):
    # Auto-generate ID
    new_id = max([item["ID"] for item in data], default=0) + 1
    new_item = {
        "ID": new_id,
        "Category": category,
        "Name": name,
        "Color": color,
        "Height": height,
        "Width": width,
        "Depth": depth,
        "Material": material,
        "Cost": cost,
        "Price": price
    }
    data.append(new_item)
    return RedirectResponse(url="/display", status_code=303)

# -------------------- Remove/Edit Form (GET) --------------------
@app.get("/remove_edit", response_class=HTMLResponse)
async def remove_edit_form(request: Request):
    return templates.TemplateResponse("remove_edit.html", {"request": request, "item": None, "not_found": False})

# -------------------- Remove/Edit Lookup (POST) --------------------
@app.post("/remove_edit")
async def remove_edit_lookup(request: Request, item_id: int = Form(...)):
    item = next((i for i in data if i["ID"] == item_id), None)
    if not item:
        return templates.TemplateResponse("remove_edit.html", {"request": request, "item": None, "not_found": True})
    return templates.TemplateResponse("remove_edit.html", {"request": request, "item": item, "not_found": False})

# -------------------- Update Item (POST) --------------------
@app.post("/update_item")
async def update_item(
    request: Request,
    item_id: int = Form(...),
    category: str = Form(...),
    name: str = Form(...),
    color: str = Form(None),
    height: float = Form(None),
    width: float = Form(None),
    depth: float = Form(None),
    material: str = Form(None),
    cost: float = Form(None),
    price: float = Form(None),
):
    item = next((i for i in data if i["ID"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.update({
        "Category": category,
        "Name": name,
        "Color": color,
        "Height": height,
        "Width": width,
        "Depth": depth,
        "Material": material,
        "Cost": cost,
        "Price": price
    })
    return RedirectResponse(url="/display", status_code=303)

# -------------------- Delete Item (POST) --------------------
@app.post("/delete_item")
async def delete_item(item_id: int = Form(...)):
    global data
    data = [i for i in data if i["ID"] != item_id]
    return RedirectResponse(url="/display", status_code=303)
