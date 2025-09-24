# src/models.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class User(Base):
    __tablename__ = 'User'
    userID = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    passwordHash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime)
    sales = relationship("Sale", back_populates="user")

class Product(Base):
    __tablename__ = 'Product'
    productID = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False)

class Sale(Base):
    __tablename__ = 'Sale'
    saleID = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey('User.userID'))
    sale_date = Column(DateTime, nullable=False)
    totalAmount = Column(Numeric(10, 2), nullable=False)
    user = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale")
    payment = relationship("Payment", uselist=False, back_populates="sale")

class SaleItem(Base):
    __tablename__ = 'SaleItem'
    saleItemID = Column(Integer, primary_key=True, autoincrement=True)
    saleID = Column(Integer, ForeignKey('Sale.saleID'))
    productID = Column(Integer, ForeignKey('Product.productID'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

class Payment(Base):
    __tablename__ = 'Payment'
    paymentID = Column(Integer, primary_key=True, autoincrement=True)
    saleID = Column(Integer, ForeignKey('Sale.saleID'))
    payment_date = Column(DateTime, nullable=False)
    payment_method = Column(String(50), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False)
    sale = relationship("Sale", back_populates="payment")

class FailedPaymentLog(Base):
    __tablename__ = 'FailedPaymentLog'
    logID = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey('User.userID'))
    attempt_date = Column(DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50), nullable=False)
    reason = Column(String(255))

