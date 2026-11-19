class OrderProcessor:

    def calculate_total(self, items, tax_rate=0.0):

        total = 0

        for item in items:

            if item["active"]:

                if item["quantity"] > 0:

                    total += item["price"] * item["quantity"]

        return total * (1 + tax_rate)


def classify_number(value):

    if value < 0:
        return "negative"

    elif value == 0:
        return "zero"

    else:
        return "positive"


def process_data(a, b, c, d, e):

    result = 0

    if a:
        if b:
            if c:
                result = d + e

    return result
