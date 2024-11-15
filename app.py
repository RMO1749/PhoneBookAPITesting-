# Import the required modules
from fastapi.exceptions import RequestValidationError
import logging
import os
from datetime import timedelta, datetime
from typing import Optional
from enum import Enum
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, validator
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from jose import JWTError, jwt
import re

# Constants and configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////app/phonebook.db")
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configure logging
logging.basicConfig(
    filename="/app/audit.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Set up SQLAlchemy
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# User database model
class User(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # Role: "READ" or "READ_WRITE"

# PhoneBook database model
class PhoneBook(Base):
    __tablename__ = "phonebook"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(100))
    phone_number = Column(String(20))

# Create tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def is_valid_phone_number(phone_number):

    # General initial validation (broad acceptance criteria)

    general_validation = (
        r"^(?:"
        r"\d{5}(?:[-.]\d{5})?|"                        # 5-digit or 5-5 patterns (e.g., 12345, 12345-12345)
        r"\d{3}[-]\d{4}|"                              # 3-4 digit pattern (e.g., 123-1234)
        r"(?:1[-. ]?)?\(?[2-9]\d{2}\)?[-. ]?[2-9]\d{2}[-. ]?\d{4}|"  # North American formats, with or without country code 1
        r"(?:\+?1[-. ]?)?(?:\(?[2-9]\d{2}\)?)?[-. ]?[2-9]\d{2}[-. ]?\d{4}|"  # Additional North American formats with optional area code
        r"(?:\+|00|011)[ ]?[1-9]\d?[ ]?\(?\d{1,4}\)?[ ]?\d{2,3}[-. ]?\d{2,4}[-. ]?\d{2,4}|"  # International with country code and optional area code
        r"(?:\+?45[ ]?\d{2}[ ]?\d{2}[ ]?\d{2}[ ]?\d{2}|"           # Danish number format with spaces
        r"\+?45[ ]?\d{4}[ ]?\d{4}|"                                # Danish format AAAA AAAA or AA AA AA AA
        r"\+?45[ ]?\d{2}\.\d{2}\.\d{2}\.\d{2})"                    # Danish format with dots
        r")$"
    )

    # Check if the phone number matches the general validation pattern
    if re.match(general_validation, phone_number):
        return True
    # Additional check for specific formats: "(XXX)XXX-XXXX" and "1(XXX)XXX-XXXX"
    if re.match(r"^\(\d{3}\)\d{3}-\d{4}$", phone_number):  # Matches (XXX)XXX-XXXX
        return True

    if re.match(r"^1\(\d{3}\)\d{3}-\d{4}$", phone_number):  # Matches 1(XXX)XXX-XXXX
        return True
    # If neither the general validation nor specific formats match, return False
    return False

# Utility function for creating access tokens
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Pydantic model for user creation with role and password validation
class UserRole(str, Enum):
    READ = "READ"
    READ_WRITE = "READ_WRITE"

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, regex=r"^[A-Za-z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)  # Adjust complexity if needed
    role: UserRole  # Use the Enum for role validation


class Token(BaseModel):
    access_token: str
    token_type: str

class Person(BaseModel):
    full_name: str = Field(..., max_length=100, regex=r"^(?:[A-Za-z]+(?:['-]?[A-Za-z]+)*,?\s*){1,3}(?:\s[A-Z]\.)?$")
    phone_number: str
    @validator("phone_number")
    def validate_phone_number(cls, value):
        if not is_valid_phone_number(value):
            raise ValueError("Invalid phone number format")
        return value

class DeleteByNameRequest(BaseModel):
    full_name: str = Field(..., max_length=100, regex=r"^(?:[A-Za-z]+(?:['-]?[A-Za-z]+)*,?\s*){1,3}(?:\s[A-Z]\.)?$")

class DeleteByNumberRequest(BaseModel):
    phone_number: str
    @validator("phone_number")
    def validate_phone_number(cls, value):
        if not is_valid_phone_number(value):
            raise ValueError("Invalid phone number format")
        return value


# Set up authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# FastAPI app initialization
app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

# Error handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )

# Authentication and User Registration
@app.post("/register", response_model=Token)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Add the user to the database
    new_user = User(username=user.username, password=user.password, role=user.role)
    db.add(new_user)
    db.commit()
    
    # Create a token
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

# Dependency to get the current user and enforce role-based access
def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code=403, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return {"username": username, "role": role}

# Update require_role function to remove the nested Depends
def require_role(required_role: str):
    def role_dependency(user=Depends(get_current_user)):
        if user["role"] != required_role and user["role"] != "READ_WRITE":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    return Depends(role_dependency)

# Define the API endpoints with role-based access
@app.get("/PhoneBook/list", dependencies=[require_role("READ")])
def list_phonebook(db: Session = Depends(get_db)):
    phonebook = db.query(PhoneBook).all()
    logging.info("Listed all entries in the phonebook")
    return phonebook

@app.post("/PhoneBook/add", dependencies=[require_role("READ_WRITE")])
def add_person(person: Person, db: Session = Depends(get_db)):
    existing_person = db.query(PhoneBook).filter_by(phone_number=person.phone_number).first()
    if existing_person:
        raise HTTPException(status_code=400, detail="Person already exists in the database")
    new_person = PhoneBook(full_name=person.full_name, phone_number=person.phone_number)
    db.add(new_person)
    db.commit()
    logging.info(f"Added new person: {person.full_name}, {person.phone_number}")
    return {"message": "Person added successfully"}

@app.put("/PhoneBook/deleteByName", dependencies=[require_role("READ_WRITE")])
def delete_by_name(request: DeleteByNameRequest, db: Session = Depends(get_db)):
    person = db.query(PhoneBook).filter_by(full_name=request.full_name).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found in the database")
    db.delete(person)
    db.commit()
    logging.info(f"Deleted person by name: {request.full_name}")
    return {"message": "Person deleted successfully"}

@app.put("/PhoneBook/deleteByNumber", dependencies=[require_role("READ_WRITE")])
def delete_by_number(request: DeleteByNumberRequest, db: Session = Depends(get_db)):
    person = db.query(PhoneBook).filter_by(phone_number=request.phone_number).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found in the database")
    db.delete(person)
    db.commit()
    logging.info(f"Deleted person by phone number: {request.phone_number}")
    return {"message": "Person deleted successfully"}
