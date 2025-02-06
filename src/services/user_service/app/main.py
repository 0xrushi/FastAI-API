# user_service/app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

# Add prefix to match the nginx routing
app = FastAPI(root_path="/users")

class User(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

users_db = []

@app.post("/", response_model=User)
async def create_user(user: User):
    user.id = len(users_db) + 1
    users_db.append(user)
    return user

@app.get("/", response_model=List[User])
async def get_users():
    return users_db

@app.get("/{user_id}", response_model=User)
async def get_user(user_id: int):
    if user_id <= 0 or user_id > len(users_db):
        raise HTTPException(status_code=404, detail="User not found")
    return users_db[user_id - 1]

@app.put("/{user_id}", response_model=User)
async def update_user(user_id: int, user: User):
    if user_id <= 0 or user_id > len(users_db):
        raise HTTPException(status_code=404, detail="User not found")
    user.id = user_id
    users_db[user_id - 1] = user
    return user

@app.delete("/{user_id}")
async def delete_user(user_id: int):
    if user_id <= 0 or user_id > len(users_db):
        raise HTTPException(status_code=404, detail="User not found")
    users_db.pop(user_id - 1)
    return {"message": "User deleted"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
