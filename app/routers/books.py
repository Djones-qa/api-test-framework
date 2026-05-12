from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app import models, schemas
from app.auth import get_current_active_user
from app.database import get_db

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=schemas.BookListResponse)
def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    genre: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    in_stock: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List all books with optional filtering and pagination."""
    query = db.query(models.Book)
    if genre:
        query = query.filter(models.Book.genre.ilike(f"%{genre}%"))
    if author:
        query = query.filter(models.Book.author.ilike(f"%{author}%"))
    if in_stock is not None:
        query = query.filter(models.Book.in_stock == in_stock)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return schemas.BookListResponse(total=total, page=page, page_size=page_size, items=items)


@router.post("", response_model=schemas.BookResponse, status_code=201)
def create_book(
    book_in: schemas.BookCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Create a new book (requires authentication)."""
    if db.query(models.Book).filter(models.Book.isbn == book_in.isbn).first():
        raise HTTPException(status_code=400, detail="ISBN already exists")

    book = models.Book(**book_in.model_dump(), owner_id=current_user.id)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.get("/{book_id}", response_model=schemas.BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Retrieve a single book by ID."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.patch("/{book_id}", response_model=schemas.BookResponse)
def update_book(
    book_id: int,
    book_in: schemas.BookUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Partially update a book (owner or any authenticated user)."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    update_data = book_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Delete a book (requires authentication)."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()
