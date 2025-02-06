from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

DATABASE_URL = "sqlite:///./shopping_cart.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)

class ShoppingCart(Base):
    __tablename__ = "shopping_carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    items = Column(String, default="")  # Stores items as a comma-separated string
    user = relationship("User")

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class UserCreate(BaseModel):
    name: str
    email: str

class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None

class ShoppingCartCreate(BaseModel):
    user_id: int
    items: str

class ShoppingCartUpdate(BaseModel):
    items: str

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# User Endpoints
@app.post("/users/", response_model=UserCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(name=user.name, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/users/{user_id}", response_model=UserUpdate)
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.name:
        db_user.name = user.name
    if user.email:
        db_user.email = user.email
    db.commit()
    return db_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted"}

# Shopping Cart Endpoints
@app.post("/cart/", response_model=ShoppingCartCreate)
def create_cart(cart: ShoppingCartCreate, db: Session = Depends(get_db)):
    db_cart = ShoppingCart(user_id=cart.user_id, items=cart.items)
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    return db_cart

@app.put("/cart/{user_id}", response_model=ShoppingCartUpdate)
def update_cart(user_id: int, cart: ShoppingCartUpdate, db: Session = Depends(get_db)):
    db_cart = db.query(ShoppingCart).filter(ShoppingCart.user_id == user_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found for this user")
    db_cart.items = cart.items
    db.commit()
    return db_cart

@app.delete("/cart/{user_id}")
def delete_cart(user_id: int, db: Session = Depends(get_db)):
    db_cart = db.query(ShoppingCart).filter(ShoppingCart.user_id == user_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found for this user")
    db.delete(db_cart)
    db.commit()
    return {"message": "Shopping cart deleted"}
