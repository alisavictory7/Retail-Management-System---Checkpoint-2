# src/models.py
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

# Use a single, shared Base for all models
# This ensures all models use the same SQLAlchemy metadata, preventing conflicts.
from src.database import Base

class User(Base):
    __tablename__ = 'User'
    userID = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False)
    _passwordHash = Column('passwordHash', String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    _created_at = Column('created_at', DateTime, default=lambda: datetime.now(timezone.utc))
    sales = relationship("Sale", back_populates="user")
    
    @property
    def passwordHash(self):
        return self._passwordHash
    
    @passwordHash.setter
    def passwordHash(self, value):
        self._passwordHash = value
    
    @property
    def created_at(self):
        return self._created_at

class Product(Base):
    __tablename__ = 'Product'
    productID = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False)
    _shipping_weight = Column('shipping_weight', Numeric(10, 2), nullable=False, default=0.0)
    _discount_percent = Column('discount_percent', Numeric(5, 2), nullable=False, default=0.0)
    _country_of_origin = Column('country_of_origin', String(255))
    _requires_shipping = Column('requires_shipping', Boolean, default=True)

    @property
    def shipping_weight(self):
        return self._shipping_weight
    
    @property
    def discount_percent(self):
        return self._discount_percent
    
    @property
    def country_of_origin(self):
        return self._country_of_origin
    
    @property
    def requires_shipping(self):
        return self._requires_shipping

    def get_discounted_unit_price(self) -> float:
        return float(self.price) * (1 - float(self._discount_percent) / 100)

    def get_shipping_fees(self, quantity: int) -> float:
        if not self._requires_shipping:
            return 0.0
        return (float(self._shipping_weight) * quantity) * 1.5

    def get_import_duty(self, quantity: int) -> float:
        if self._country_of_origin == 'USA':
            return 0.0
        return float(self.price) * quantity * 0.05
        
    def get_subtotal_for_quantity(self, quantity: int) -> float:
        return self.get_discounted_unit_price() * quantity


class Sale(Base):
    __tablename__ = 'Sale'
    saleID = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey('User.userID'))
    _sale_date = Column('sale_date', DateTime, nullable=False)
    _totalAmount = Column('totalAmount', Numeric(10, 2), nullable=False)
    _status = Column('status', String(50))
    user = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale")
    payments = relationship("Payment", back_populates="sale")
    
    @property
    def sale_date(self):
        return self._sale_date
    
    @sale_date.setter
    def sale_date(self, value):
        self._sale_date = value
    
    @property
    def totalAmount(self):
        return self._totalAmount
    
    @totalAmount.setter
    def totalAmount(self, value):
        self._totalAmount = value
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value

class SaleItem(Base):
    __tablename__ = 'SaleItem'
    saleItemID = Column(Integer, primary_key=True, autoincrement=True)
    saleID = Column(Integer, ForeignKey('Sale.saleID'))
    productID = Column(Integer, ForeignKey('Product.productID'))
    quantity = Column(Integer, nullable=False)
    _original_unit_price = Column('original_unit_price', Numeric(10, 2), nullable=False)
    _final_unit_price = Column('final_unit_price', Numeric(10, 2), nullable=False)
    _discount_applied = Column('discount_applied', Numeric(10, 2), nullable=False)
    _shipping_fee_applied = Column('shipping_fee_applied', Numeric(10, 2), nullable=False)
    _import_duty_applied = Column('import_duty_applied', Numeric(10, 2), nullable=False)
    _subtotal = Column('subtotal', Numeric(10, 2), nullable=False)
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")
    
    @property
    def original_unit_price(self):
        return self._original_unit_price
    
    @original_unit_price.setter
    def original_unit_price(self, value):
        self._original_unit_price = value
    
    @property
    def final_unit_price(self):
        return self._final_unit_price
    
    @final_unit_price.setter
    def final_unit_price(self, value):
        self._final_unit_price = value
    
    @property
    def discount_applied(self):
        return self._discount_applied
    
    @discount_applied.setter
    def discount_applied(self, value):
        self._discount_applied = value
    
    @property
    def shipping_fee_applied(self):
        return self._shipping_fee_applied
    
    @shipping_fee_applied.setter
    def shipping_fee_applied(self, value):
        self._shipping_fee_applied = value
    
    @property
    def import_duty_applied(self):
        return self._import_duty_applied
    
    @import_duty_applied.setter
    def import_duty_applied(self, value):
        self._import_duty_applied = value
    
    @property
    def subtotal(self):
        return self._subtotal
    
    @subtotal.setter
    def subtotal(self, value):
        self._subtotal = value

class Payment(Base):
    __tablename__ = 'Payment'
    paymentID = Column(Integer, primary_key=True)
    saleID = Column(Integer, ForeignKey('Sale.saleID'))
    _payment_date = Column('payment_date', DateTime, default=lambda: datetime.now(timezone.utc))
    amount = Column(Numeric(10, 2))
    _status = Column('status', String(20))
    _payment_type = Column('payment_type', String(50))
    type = Column(String(50))  # This line is required for polymorphic identity
    sale = relationship("Sale", back_populates="payments")
    __mapper_args__ = {
        'polymorphic_identity': 'payment',
        'polymorphic_on': type
    }
    
    @property
    def payment_date(self):
        return self._payment_date
    
    @payment_date.setter
    def payment_date(self, value):
        self._payment_date = value
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value
    
    @property
    def payment_type(self):
        return self._payment_type
    
    @payment_type.setter
    def payment_type(self, value):
        self._payment_type = value

    def authorized(self) -> (bool, str):
        # Default behavior: always authorized
        return True, "Approved"

class Cash(Payment):
    _cash_tendered = Column('cash_tendered', Numeric(10, 2))
    __mapper_args__ = {'polymorphic_identity': 'cash'}
    
    @property
    def cash_tendered(self):
        return self._cash_tendered
    
    @cash_tendered.setter
    def cash_tendered(self, value):
        self._cash_tendered = value

class Card(Payment):
    _card_number = Column('card_number', String(255))
    _card_type = Column('card_type', String(50))
    _card_exp_date = Column('card_exp_date', String(7)) # MM/YYYY
    __mapper_args__ = {'polymorphic_identity': 'card'}
    
    @property
    def card_number(self):
        return self._card_number
    
    @card_number.setter
    def card_number(self, value):
        self._card_number = value
    
    @property
    def card_type(self):
        return self._card_type
    
    @card_type.setter
    def card_type(self, value):
        self._card_type = value
    
    @property
    def card_exp_date(self):
        return self._card_exp_date
    
    @card_exp_date.setter
    def card_exp_date(self, value):
        self._card_exp_date = value

    def authorized(self) -> (bool, str):
        card_num_str = self._card_number.strip() if self._card_number else ""
        if not card_num_str.isdigit() or not (15 <= len(card_num_str) <= 19):
            return False, "Invalid Card Number (must be 15-19 digits)"
        try:
            exp_month, exp_year = map(int, self._card_exp_date.split('/'))
            current_date = datetime.now(timezone.utc)
            if (exp_year < current_date.year) or (exp_year == current_date.year and exp_month < current_date.month):
                return False, "Card Expired"
        except (ValueError, TypeError):
            return False, "Invalid Expiry Date Format"
        if "1111" in self._card_number:
            return False, "Card Declined by issuer"
        return True, "Approved"

class FailedPaymentLog(Base):
    __tablename__ = 'FailedPaymentLog'
    logID = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey('User.userID'))
    _attempt_date = Column('attempt_date', DateTime, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    _payment_method = Column('payment_method', String(50), nullable=False)
    _reason = Column('reason', String(255))
    
    @property
    def attempt_date(self):
        return self._attempt_date
    
    @attempt_date.setter
    def attempt_date(self, value):
        self._attempt_date = value
    
    @property
    def payment_method(self):
        return self._payment_method
    
    @payment_method.setter
    def payment_method(self, value):
        self._payment_method = value
    
    @property
    def reason(self):
        return self._reason
    
    @reason.setter
    def reason(self, value):
        self._reason = value

