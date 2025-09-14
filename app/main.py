from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
    )

@app.get("/search")
def search(barcode: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, description, stock FROM products WHERE barcode = %s", (barcode,))
    row = cur.fetchone()
    conn.close()

    if row:
        return {"barcode": barcode, "name": row[0], "description": row[1], "stock": row[2]}
    else:
        return {"error": "Not found"}
