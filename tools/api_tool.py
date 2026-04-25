import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional
import plotext as plt

def get_internal_currency_code(currency_code: str) -> Optional[str]:
    """
    Получает внутренний код валюты (например, R01235 для USD)
    из API ЦБ РФ.

    Args:
        currency_code: Трехбуквенный код валюты (напиример USD)

    Returns:
        Внутренний код валюты или None, если не найден
    """
    
    url = "http://www.cbr.ru/scripts/XML_daily.asp"
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'windows-1251'
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            for valute in root.findall('Valute'):
                char_code_elem = valute.find('CharCode')
                if char_code_elem is not None and char_code_elem.text == currency_code:
                    internal_id = valute.get('ID')
                    if internal_id:
                        return internal_id
    except Exception as e:
        print(f"Ошибка при получении внутреннего кода {currency_code}: {e}")
    
    return None

def get_historical_information(currency: str, start_date: str, end_date: str) -> list:
    """
    Получает исторические курсы валюты за период.
    
    Args:
        currency: Буквенный код валюты (например USD)
        start_date: Начальная дата в формате ДД.ММ.ГГГГ
        end_date: Конечная дата в формате ДД.ММ.ГГГГ
    
    Returns:
        Список с курсами за каждый день
    """
    if currency.upper() == "RUB":
        return [{
            "currency": "RUB", 
            "rate": 1.0, 
            "start_date": start_date,
            "end_date": end_date,
            "note": "Рубль — базовая валюта ЦБ РФ. Курс рубля к рублю всегда равен 1."
        }]
    internal_code = get_internal_currency_code(currency)
    if not internal_code:
        print(f"Не удалось найти внутренний код для валюты {currency}")
        return []

    url = "http://www.cbr.ru/scripts/XML_dynamic.asp"
    start_date_fixed = start_date.replace('.', '/')
    end_date_fixed = end_date.replace('.', '/')
    
    params = {
        'date_req1': start_date_fixed,
        'date_req2': end_date_fixed,
        'VAL_NM_RQ': internal_code
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.encoding = 'windows-1251'
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            historical_data = []
            
            for record in root.findall('Record'):
                date_str = record.get('Date')
                if date_str is None:
                    continue
                
                current_date = datetime.strptime(date_str, "%d.%m.%Y").date()
                value_elem = record.find('Value')
                
                if value_elem is not None and value_elem.text is not None:
                    rate = float(value_elem.text.replace(',', '.'))
                    historical_data.append({
                        'currency': currency,
                        'rate': rate,
                        'date': current_date
                    })
            
            return historical_data
        else:
            return []
            
    except Exception as e:
        print(f"Ошибка при получении исторической информации: {e}")
        return []

def get_currency_rate(currency: str, date: Optional[str] = None) -> dict:
    """Получает курс валюты на конкретную дату"""
    url = "http://www.cbr.ru/scripts/XML_daily.asp"
    if currency.upper() == "RUB":
            return {"currency": "RUB", "rate": 1.0, "date": datetime.now().date(),
                "note": "Рубль является базовой валютой ЦБ РФ, курс всегда равен 1"}
    
    if date:
        url += f"?date_req={date}"
    
    try:
        
        response = requests.get(url, timeout=10)
        response.encoding = 'windows-1251'
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            
            date_str = root.get('Date')
            if date_str is None:
                return {}
            
            current_date = datetime.strptime(date_str, '%d.%m.%Y').date()
            
            for valute in root.findall('Valute'):
                char_code_elem = valute.find('CharCode')
                if char_code_elem is not None and char_code_elem.text == currency:
                    value_elem = valute.find('Value')
                    if value_elem is not None and value_elem.text is not None:
                        rate = float(value_elem.text.replace(',', '.'))
                        return {
                            'currency': currency,
                            'rate': rate,
                            'date': current_date
                        }
    except Exception as e:
        print(f"Ошибка при получении курса {currency}: {e}")
    
    return {}

def show_graph(currency: str, start_date: str, end_date: str):
    information = get_historical_information(currency, start_date, end_date)
    
    dates = [item['date'].strftime('%d/%m/%Y') for item in information]
    rates = [item['rate'] for item in information]
    
    plt.plot(dates, rates)
    plt.title(f'Курс {currency} к рублю')
    plt.xlabel('Дата')
    plt.ylabel(f'Курс {currency}/RUB')
    plt.show()
    return {
        "currency": currency,
        "period": {"start": start_date, "end": end_date},
        "statistics": {
            "min": min(rates),
            "max": max(rates),
            "avg": sum(rates) / len(rates),
            "points_count": len(rates)
        },
        "first_date": dates[0],
        "last_date": dates[-1]
    }