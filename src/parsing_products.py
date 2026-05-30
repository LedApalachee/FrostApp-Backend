import re

# Паттерн лучше вынести вне функции
# число обязательно, ИЛИ единица стоит после запятой/пробела в конце строки
pattern = r"(\d+(?:[.,]\d+)?)\s*(кг|г|мл|л|шт)\b|[,\s]+(кг|г|мл|л|шт)\b"

"""
Тут я запутался, но если идея была таковой, что мы вытаскиваем из названия (прим. "1.5л"), то
мы потом че "1,5" записываем в quantity? а units - "л"? 
Я потому что сначала подумал что мы именно из чека просто берем quantity готовое, а 1,5л просто отсекаем
А сейчас вообще подумал, что если приходит продукт name: "Молоко 1,5л" , quantity: 2, то не лучше ли сделать
quantity = 1,5*2 =3
units = "л"
Я сделаю так, но вы поправьте если не праивльно
"""


def extract_unit(products) -> list:
    result = []

    for product in products:
        name_s = product.get("name", "")
        quantity = product.get("quantity", 1)
        match = re.search(pattern, name_s.lower())

        if match:
            if match.group(1):  # нашли число + единицу
                number = match.group(1).replace(",", ".")
                unit = match.group(2)
                quantity *= float(number)
            else:  # нашли только единицу (случай "Лук репчатый, кг")
                unit = match.group(3)
            name = product["name"][: match.start()].strip(" ,.-")
        else:
            unit = "шт"
            name = product["name"]
        price = product["price"]

        result.append({"name": name, "quantity": quantity, "unit": unit, "price": price})

    return result
