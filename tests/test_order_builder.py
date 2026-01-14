import json
from chat_services.order_builder import build_order

def test_build_order_empty():
    # Verifica il comportamento con una lista vuota
    order_list, order_json = build_order([])
    assert order_list == []
    assert order_json == "[]"

def test_build_order_with_delivery_data():
    # Verifica che i dati di consegna siano estratti correttamente [cite: 98]
    criteria = [{
        "delivery_type": "domicilio",
        "delivery_day": "2025-05-16",
        "delivery_hour": "20:00",
        "address": "Via Roma 15",
        "confirmed_products": []
    }]
    order_list, _ = build_order(criteria)
    
    assert len(order_list) == 1
    assert order_list[0]["delivery_type"] == "domicilio"
    assert order_list[0]["address"] == "Via Roma 15"

def test_build_order_product_resolution():
    # Verifica che i nomi dei prodotti vengano risolti tramite alias [cite: 99]
    criteria = [{
        "confirmed_products": [
            {"name": "uramaki piccante", "quantity": 2}
        ]
    }]
    # Passiamo menu_cache=None per non testare la parte di DB (unit test puro)
    order_list, _ = build_order(criteria, menu_cache=None)
    
    # Il nome deve essere diventato quello canonico [cite: 101]
    resolved_name = order_list[0]["products"][0]["original_product"]["name"]
    assert resolved_name == "uramaki sunburn"