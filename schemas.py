"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- BlogPost -> "blogpost" collection
- CaseStudy -> "casestudy" collection
- Project -> "project" collection
- Chat -> "chat" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict

# Example schemas can stay for reference but are unused by the app
class User(BaseModel):
    name: str
    email: str
    address: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: bool = True

class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    in_stock: bool = True

# --- App Schemas ---

class BlogPost(BaseModel):
    title: str
    content: str
    tags: List[str] = []
    cover_url: Optional[HttpUrl] = None
    author: Optional[str] = None

class CaseStudy(BaseModel):
    title: str
    summary: str
    problem: str
    solution: str
    impact: str
    images: List[HttpUrl] = []
    links: Dict[str, HttpUrl] = {}

class Project(BaseModel):
    title: str
    description: str
    tech_stack: List[str] = []
    repo_url: Optional[HttpUrl] = None
    live_url: Optional[HttpUrl] = None
    featured: bool = False

class Chat(BaseModel):
    role: str  # "user" | "assistant"
    message: str
