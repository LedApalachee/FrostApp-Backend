import re

def parsing_func(products):
    # число обязательно, ИЛИ единица стоит после запятой/пробела в конце строки
    pattern = r"(\d+(?:[.,]\d+)?)\s*(кг|г|мл|л|шт)\b|[,\s]+(кг|г|мл|л|шт)\b"

    result = []

    for product in products:
        match = re.search(pattern, product.lower())

        if match:
            if match.group(1):  # нашли число + единицу
                number = match.group(1)
                unit = match.group(2)
            else:  # нашли только единицу (случай "Лук репчатый, кг")
                number = "1"
                unit = match.group(3)
            weight = f"{number}{unit}"
            name = product[:match.start()].strip(" ,.-")
        else:
            weight = None
            name = product

        result.append({
            "name": name,
            "weight": weight
        })

    return result