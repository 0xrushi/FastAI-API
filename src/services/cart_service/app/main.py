# cart_service/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

# Add prefix to match the nginx routing
app = FastAPI(root_path="/cart")

class CartItem(BaseModel):
    id: Optional[int] = None
    user_id: int
    product_name: str
    quantity: int

carts_db = []

@app.post("/", response_model=CartItem)
async def create_cart_item(cart_item: CartItem):
    cart_item.id = len(carts_db) + 1
    carts_db.append(cart_item)
    return cart_item

@app.get("/user/{user_id}", response_model=List[CartItem])
async def get_user_cart(user_id: int):
    user_cart = [item for item in carts_db if item.user_id == user_id]
    return user_cart

@app.put("/{item_id}", response_model=CartItem)
async def update_cart_item(item_id: int, cart_item: CartItem):
    if item_id <= 0 or item_id > len(carts_db):
        raise HTTPException(status_code=404, detail="Cart item not found")
    cart_item.id = item_id
    carts_db[item_id - 1] = cart_item
    return cart_item

@app.delete("/{item_id}")
async def delete_cart_item(item_id: int):
    if item_id <= 0 or item_id > len(carts_db):
        raise HTTPException(status_code=404, detail="Cart item not found")
    carts_db.pop(item_id - 1)
    return {"message": "Cart item deleted"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
