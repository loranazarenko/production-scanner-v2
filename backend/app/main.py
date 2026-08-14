import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session

# =========================
#  Настройки базы (SQLite)
# =========================

# Для полноценного демо используем SQLite-файл вместо Postgres.
# Это реальная база (таблицы, записи), но без внешних зависимостей.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "scanner.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # важно для SQLite в FastAPI
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =========================
#  Модели SQLAlchemy
# =========================

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    operations = relationship(
        "ProductionOperation",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductionOperation(Base):
    __tablename__ = "production_operations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    operation_code = Column(String, nullable=False)
    operation_name = Column(String, nullable=False)
    performed_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="operations")


# =========================
#  Pydantic DTO
# =========================

class OperationDto(BaseModel):
    id: int
    code: str
    name: str


class LastOperationDto(BaseModel):
    id: int
    operation_code: str
    operation_name: str
    performed_at: datetime


class BarcodeInfoResponse(BaseModel):
    barcode: str
    available_operations: List[OperationDto]
    last_operation: Optional[LastOperationDto]


class CompleteOperationRequest(BaseModel):
    barcode: str
    operation_code: str


# =========================
#  FastAPI приложение
# =========================

app = FastAPI(
    title="Production Scanner API (SQLite)",
    version="1.0.0",
    description="JSON API для сканера производства с хранением операций в SQLite",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
#  Dependency для сессии БД
# =========================

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
#  Хук старта приложения
# =========================

@app.on_event("startup")
def on_startup() -> None:
    # Создаём таблицы, если их ещё нет
    Base.metadata.create_all(bind=engine)


# =========================
#  Эндпоинты API
# =========================

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/barcodes/{barcode}", response_model=BarcodeInfoResponse)
def get_barcode_info(barcode: str, db: Session = Depends(get_db)) -> BarcodeInfoResponse:
    # Находим или создаём продукт по штрих-коду
    product = db.query(Product).filter(Product.barcode == barcode).first()
    if product is None:
        product = Product(barcode=barcode, description=None)
        db.add(product)
        db.commit()
        db.refresh(product)

    # Справочник доступных операций (пока захардкожен)
    available_operations = [
        OperationDto(id=1, code="CUT", name="Резка"),
        OperationDto(id=2, code="WELD", name="Сварка"),
        OperationDto(id=3, code="PACK", name="Упаковка"),
    ]

    # Находим последнюю выполненную операцию по этому продукту
    last_op_row = (
        db.query(ProductionOperation)
        .filter(ProductionOperation.product_id == product.id)
        .order_by(ProductionOperation.performed_at.desc())
        .first()
    )

    last_op: Optional[LastOperationDto] = None
    if last_op_row is not None:
        last_op = LastOperationDto(
            id=last_op_row.id,
            operation_code=last_op_row.operation_code,
            operation_name=last_op_row.operation_name,
            performed_at=last_op_row.performed_at,
        )

    return BarcodeInfoResponse(
        barcode=barcode,
        available_operations=available_operations,
        last_operation=last_op,
    )


@app.post("/api/operations/complete")
def complete_operation(
    payload: CompleteOperationRequest,
    db: Session = Depends(get_db),
) -> dict:
    # Находим или создаём продукт по штрих-коду
    product = db.query(Product).filter(Product.barcode == payload.barcode).first()
    if product is None:
        product = Product(barcode=payload.barcode, description=None)
        db.add(product)
        db.commit()
        db.refresh(product)

    # Человеческие названия операций
    operation_names = {
        "CUT": "Резка",
        "WELD": "Сварка",
        "PACK": "Упаковка",
    }
    name = operation_names.get(payload.operation_code, payload.operation_code)

    # Записываем операцию
    op = ProductionOperation(
        product_id=product.id,
        operation_code=payload.operation_code,
        operation_name=name,
    )
    db.add(op)
    db.commit()
    db.refresh(op)

    return {
        "success": True,
        "message": "Операция сохранена",
        "operation_id": op.id,
        "performed_at": op.performed_at,
    }