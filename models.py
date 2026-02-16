from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import date
from typing import List
from decimal import Decimal, ROUND_HALF_UP
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[ logging.FileHandler("app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__)

class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")
    street: str | None= Field(None, description="Street and number")
    city: str | None= Field(None, description="City")
    zip_code: str | None= Field(None, description="ZIP code")
    country: str | None= Field(None, description="Country")
    district: str | None = Field(None, description="İlçe (for TR)")
    neighborhood: str | None = Field(None, description="Mahalle (for TR)")

class InvoiceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    description: str = Field(description="Description of the invoice item")
    quantity: int | None = Field(None,description="Quantity of the invoice item - quantity can be negative for returns or credit notes")
    unit_price: Decimal | None = Field(None,ge=0, description="Unit price of the invoice item")

    tax_rate: Decimal | None = Field(None,ge=0,  le=100, description="Tax rate of the invoice item")
    tax_amount: Decimal | None = Field(None,ge=0, description="Tax amount for the invoice item")

    discount_amount: Decimal | None = Field(None,ge=0, description="Discount on the invoice item")
    discount_rate: Decimal | None = Field(None,ge=0, le=100, description="Discount rate for the invoice item")

    # Amount hyerarchy: gross_amount -> net_amount -> total_amount
    gross_amount: Decimal | None = Field(None,ge=0, description="Amount before discount and tax")
    net_amount: Decimal | None = Field(None,ge=0, description="Amount before tax and after discount")
    total_amount: Decimal | None = Field(None,ge=0, description="Total price of the invoice item (net + tax)")

    tevkifat_rate: Decimal | None = Field(None,ge=0, description="Tevkifat rate for TR invoices")

    @model_validator(mode="after")
    def check_financial_consistency(self):
        logger.info("Validating financial consistency for invoice item: %s", self.description)
        """
        Financial Consistency Check
        Schema: Quantity * Price -> Gross -> Net -> Tax -> Total
        """

        tolerance = Decimal("0.5")
        decimal_places = Decimal("0.01")
        rounding_mode = ROUND_HALF_UP

        self.normalize_rates()

        if self.quantity is not None and self.unit_price is not None:
            gross = self.calculate_gross(tolerance, decimal_places, rounding_mode)
            self.calculate_discount(gross, tolerance, decimal_places, rounding_mode)
            self.calculate_net(gross, tolerance)

        elif self.total_amount is not None:
            self.calculate_net_and_tax_from_total(tolerance, decimal_places, rounding_mode)

        elif self.gross_amount is not None:
            self.calculate_from_gross(tolerance, decimal_places, rounding_mode)

        elif self.net_amount is not None:
            self.calculate_from_net(tolerance, decimal_places, rounding_mode)
        else:
            error_msg = f"Insufficient financial information for invoice item: {self.description}. At least one of the following must be provided: (quantity and unit price), total amount, gross amount, or net amount."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.calculate_final_taxes_and_totals(tolerance, decimal_places, rounding_mode)

        return self

    def normalize_rates(self):
        logger.debug("Normalizing rates for invoice item: %s", self.description)
        if self.tax_rate is not None:
            if self.tax_rate > 1:
                self.tax_rate = self.tax_rate / Decimal(100)
        if self.discount_rate is not None:
            if self.discount_rate > 1:
                self.discount_rate = self.discount_rate / Decimal(100)

    def calculate_gross(self, tolerance, decimal_places, rounding_mode):
        logger.info("Calculating gross amount for invoice item: %s", self.description)
        gross = (self.quantity * self.unit_price).quantize(decimal_places, rounding=rounding_mode)
        if self.gross_amount is None:
            self.gross_amount = gross
        elif abs(self.gross_amount - gross) > tolerance:
            error_msg = f"Gross amount {self.gross_amount} does not match calculated gross {gross} for item: {self.description}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return gross
            
    def calculate_discount(self, gross, tolerance, decimal_places, rounding_mode):
        #DISCOUNT LOGIC: if both discount amount and rate are provided, check consistency. If only one is provided, calculate the other. If neither is provided, assume no discount.
        logger.info("Calculating discount for invoice item: %s", self.description)
        if self.discount_amount is None:
            if self.discount_rate is not None:
                self.discount_amount = (gross * self.discount_rate).quantize(decimal_places, rounding=rounding_mode)
            else:
                self.discount_amount = Decimal(0)

        if self.discount_rate is None:
            if self.discount_amount is not None and gross > 0:
                self.discount_rate = (self.discount_amount / gross).quantize(Decimal("0.0001"), rounding=rounding_mode)
            else:
                self.discount_rate = Decimal(0)

        if self.discount_amount is not None and self.discount_rate is not None:
            expected_discount_amount = (gross * self.discount_rate).quantize(decimal_places, rounding=rounding_mode)
            if abs(self.discount_amount - expected_discount_amount) > tolerance:
                error_msg = f"Discount amount {self.discount_amount} does not match calculated discount {expected_discount_amount} for item: {self.description}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
    def calculate_net(self, gross, tolerance):
        logger.info("Calculating net amount for invoice item: %s", self.description)
        net = gross - self.discount_amount
        if self.net_amount is None:
            self.net_amount = net
        elif abs(self.net_amount - net) > tolerance:
            error_msg = f"Net amount {self.net_amount} does not match calculated net {net} for item: {self.description}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        #SCENARIO 2: If total amount is provided but net amount is missing, calculate net amount using tax rate or tax amount if available. If tax amount is missing but net amount is available, calculate tax amount.
    def calculate_net_and_tax_from_total(self, tolerance, decimal_places, rounding_mode):
            logger.info("Calculating net and tax from total amount for invoice item: %s", self.description)
            if self.net_amount is None:
                if self.tax_rate is not None:
                    tax_multiplier = Decimal(1) + self.tax_rate
                    net = (self.total_amount / tax_multiplier).quantize(decimal_places, rounding=rounding_mode)
                    self.net_amount = net
                elif self.tax_amount is not None:
                    self.net_amount = self.total_amount - self.tax_amount
                else:
                    self.net_amount = self.total_amount
            
            if self.tax_amount is None and self.net_amount is not None:
                self.tax_amount = self.total_amount - self.net_amount
            
            if self.gross_amount is None and self.net_amount is not None:
                disc = self.discount_amount if self.discount_amount is not None else Decimal(0)
                self.gross_amount = self.net_amount + disc
        
        #SCENARIO 3:
    def calculate_from_gross(self, decimal_places, rounding_mode):
        logger.info("Calculating net, discount, tax, and total from gross amount for invoice item: %s", self.description)
        rate = self.discount_rate if self.discount_rate is not None else Decimal(0)
        self.discount_amount = (self.gross_amount * rate).quantize(decimal_places, rounding=rounding_mode)

        if self.net_amount is None:
                self.net_amount = self.gross_amount - self.discount_amount

    def calculate_from_net(self):
        logger.info("Calculating gross, discount, tax, and total from net amount for invoice item: %s", self.description)
        if self.gross_amount is None:
            self.gross_amount = self.net_amount
            self.discount_amount = Decimal(0)
        
    def calculate_final_taxes_and_totals(self, tolerance, decimal_places, rounding_mode):
        logger.info("Calculating final taxes and totals for invoice item: %s", self.description)
        if self.tax_rate is not None and self.tax_amount is None and self.net_amount is not None:
            self.tax_amount = (self.net_amount * self.tax_rate).quantize(decimal_places, rounding=rounding_mode)
        
        safe_tax = self.tax_amount if self.tax_amount is not None else Decimal(0)
        safe_net = self.net_amount if self.net_amount is not None else Decimal(0)

        expected_total = safe_net + safe_tax
        if self.total_amount is None:
            self.total_amount = expected_total
        elif abs(self.total_amount - expected_total) > tolerance:
            error_msg = f"Total amount {self.total_amount} does not match expected total {expected_total} for item: {self.description}"
            logger.error(error_msg)
            raise ValueError(error_msg)    

class Invoice(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    invoice_number: str = Field(min_length=1, description="Invoice number")
    invoice_date: date = Field(description="Invoice date")
    due_date: date | None = Field(None, description="Due date")
    invoice_type: str | None = Field(None, description="Type of the invoice (e.g., standard, proforma) / for TR invoices: SATIS , IADE, TEVKIFAT")

    company_name: str = Field(min_length=2, description="Name of the company")
    company_address: Address = Field(description="Address of the company")
    company_tax_info: str | None = Field(None, description="Tax information of the company (e.g., tax ID)")

    customer_name : str | None = Field(None, description="Name of the customer")
    customer_address: Address | None = Field(None, description="Address of the customer")
    customer_tax_info: str | None = Field(None, description="Tax information of the customer (e.g., tax ID)")

    #FOR TURKISH INVOICES
    company_tax_office: str | None = Field(None, description="Tax office of the company (for TR invoices)")
    ettn: str | None = Field(None, description="Ettn code for TR invoices")
    vkn_tckn: str | None = Field(None, description="VKN or TCKN for TR invoices")
    ticaret_sicil_no: str | None = Field(None, description="Trade registry number for TR invoices")

    items: List[InvoiceItem] = Field(default_factory=list, description="List of invoice items")

    subtotal: Decimal | None = Field(None, ge=0, description="Subtotal before discounts and taxes")
    total_discount: Decimal | None = Field(None, ge=0, description="Global Discount")
    total_tax: Decimal | None = Field(None, ge=0, description="Total tax amount")
    total_amount: Decimal = Field(ge=0, description="Total amount of the invoice")

    currency: str = Field(min_length=3, max_length=3, description="Currency of the invoice")

    @field_validator("currency")
    def validate_currency(cls, value):
        logger.info("Validating currency: %s", value)
        value = value.upper()
        if not value.isalpha() or len(value) != 3:
            error_msg = f"Currency '{value}' is invalid. Currency must be a 3-letter alphabetic code."
            logger.error(error_msg)
            raise ValueError(error_msg)
        return value
    
    @field_validator("due_date")
    def validate_due_date(cls, value, info):
        logger.info("Validating due date: %s", value)
        if value is not None and value < info.data.get("invoice_date"):
            error_msg = f"Due date {value} cannot be earlier than invoice date {info.data.get('invoice_date')}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        return value
    
    @model_validator(mode="after")
    def calculate_totals(self):
        logger.info("Calculating totals for invoice: %s", self.invoice_number)
        if not self.items or len(self.items) == 0:
            return self

        calculated_subtotal = Decimal(0)
        calculated_tax = Decimal(0)
        tolerance = Decimal("1.0")
        decimal_places = Decimal("0.01")
        rounding_mode = ROUND_HALF_UP

        for item in self.items:
            if item.net_amount is not None:
                calculated_subtotal += item.net_amount
            if item.tax_amount is not None:
                calculated_tax += item.tax_amount
            
        calculated_subtotal = calculated_subtotal.quantize(decimal_places, rounding=rounding_mode)
        calculated_tax = calculated_tax.quantize(decimal_places, rounding=rounding_mode)

        self.finalize_calculations(tolerance, decimal_places, rounding_mode, calculated_subtotal, calculated_tax)

        return self

    def finalize_calculations(self, tolerance, decimal_places, rounding_mode, calculated_subtotal, calculated_tax):
        logger.info("Finalizing calculations for invoice: %s", self.invoice_number)
        if self.total_discount is not None and self.total_discount > 0:
            calculated_subtotal -= self.total_discount.quantize(decimal_places, rounding=rounding_mode)

        calculated_total = (calculated_subtotal + calculated_tax).quantize(decimal_places, rounding=rounding_mode)

        if self.subtotal is None or self.subtotal == Decimal(0):
            self.subtotal = calculated_subtotal
        elif abs(self.subtotal - calculated_subtotal) > tolerance:
            error_msg = f"Subtotal {self.subtotal} does not match calculated subtotal {calculated_subtotal}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if self.total_tax is None or self.total_tax == Decimal(0):
            self.total_tax = calculated_tax
        elif abs(self.total_tax - calculated_tax) > tolerance:
            error_msg = f"Total tax {self.total_tax} does not match calculated tax {calculated_tax}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if self.total_amount is None or self.total_amount == Decimal(0):
            self.total_amount = calculated_total
        elif abs(self.total_amount - calculated_total) > tolerance:
            error_msg = f"Total amount {self.total_amount} does not match calculated total {calculated_total}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        return self



