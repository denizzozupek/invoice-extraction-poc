import pytest
from decimal import Decimal
from models import InvoiceItem, Address, Invoice
from datetime import date

def test_invoice_item_math_logic():
    """AI'ın sadece birim fiyat ve KDV oranını bulduğu senaryoyu test eder."""

    item_data = {
        "description": "Yeni .com alan adı kaydı (heraklesindefteri.com)",
        "quantity": 1,
        "unit_price": Decimal("125.03"),
        "tax_rate": Decimal("20.00")

    }


    item = InvoiceItem(**item_data)

    assert item.gross_amount == Decimal("125.03"), "Brüt hatalı!"
    assert item.discount_amount == Decimal("0.00"), "İndirim sıfır olmalıydı!"
    assert item.net_amount == Decimal("125.03"), "Net tutar hatalı!"
    assert item.tax_amount == Decimal("25.01"), "KDV tutarı hatalı (25.01 olmalıydı)!"
    assert item.total_amount == Decimal("150.04"), "Genel toplam hatalı!"
    
    print("\n✅ InvoiceItem Matematiği KUSURSUZ Çalışıyor!")

def test_missing_data_raises_error():
    """Eksik veri geldiğinde sistemin çöküp çökmediğini (hata fırlattığını) test eder."""
    
    item_data = {
        "description": "Hatalı Ürün",
    }


    with pytest.raises(ValueError):
        InvoiceItem(**item_data)
        
    print("\n✅ Savunma Sistemi (Defensive Programming) KUSURSUZ Çalışıyor!")