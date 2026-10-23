"""Modelos SQLAlchemy 2.0 (OLTP del Anexo A + users, etl_runs y tablas analíticas).

Las fechas se guardan como hora local naive (Colombia, UTC-5).
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def dinero():
    return Numeric(12, 2, asdecimal=False)


class ProductModel(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    unit_price: Mapped[float] = mapped_column(dinero(), nullable=False)
    unit_cost: Mapped[float] = mapped_column(dinero(), nullable=False, default=0)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CustomerModel(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    encrypted_email: Mapped[str | None] = mapped_column(Text)
    encrypted_phone: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class SaleModel(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    total_amount: Mapped[float] = mapped_column(dinero(), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)
    items: Mapped[list["SaleItemModel"]] = relationship(back_populates="sale", cascade="all, delete-orphan",
                                                        order_by="SaleItemModel.id")


class SaleItemModel(Base):
    __tablename__ = "sale_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(dinero(), nullable=False)
    subtotal: Mapped[float] = mapped_column(dinero(), nullable=False)
    sale: Mapped[SaleModel] = relationship(back_populates="items")
    product: Mapped[ProductModel] = relationship()


class InventoryMovementModel(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ----- Dominio analítico / ETL (los llena la Fase 2) -----

class EtlRunModel(Base):
    __tablename__ = "etl_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    watermark: Mapped[datetime | None] = mapped_column(DateTime)  # última venta procesada
    rows_extracted: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


class DemandForecastModel(Base):
    __tablename__ = "analytics_demand_forecast"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon: Mapped[int] = mapped_column(Integer, nullable=False)  # 7 o 30 días
    predicted_qty: Mapped[float] = mapped_column(Numeric(12, 3, asdecimal=False), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    __table_args__ = (Index("ix_forecast_prod_horizon", "product_id", "horizon"),)


class MarketBasketRuleModel(Base):
    __tablename__ = "analytics_market_basket_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    antecedent: Mapped[str] = mapped_column(String(255), nullable=False)
    consequent: Mapped[str] = mapped_column(String(255), nullable=False)
    support: Mapped[float] = mapped_column(Numeric(8, 6, asdecimal=False), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(8, 6, asdecimal=False), nullable=False)
    lift: Mapped[float] = mapped_column(Numeric(10, 4, asdecimal=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CustomerSegmentModel(Base):
    __tablename__ = "analytics_customer_segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    recency: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    monetary: Mapped[float] = mapped_column(dinero(), nullable=False)
    cluster: Mapped[int] = mapped_column(Integer, nullable=False)
    segment_label: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
