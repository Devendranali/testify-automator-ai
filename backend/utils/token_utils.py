def calculate_cost(model: str, total_tokens: int) -> float:
    pricing = {
        "gpt-4o": 10,
        "gpt-4o-mini": 1,
    }
    price = pricing.get(model, 10)
    total = total_tokens or 0
    return (total / 1_000_000) * price
