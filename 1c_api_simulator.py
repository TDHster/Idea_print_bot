from fastapi import FastAPI

app = FastAPI()

# Словарь с заказами и их количествами
orders = {
    "0131846510-0011": 1,
    "0131846510-0012": 2,
    "0131846510-0013": 1,
}

@app.get("/markets/hs/api_bot/getpath/{order_number}")
def get_path(order_number: str):
    if not order_number:
        return {"result": False, "info": "Invalid request format"}

    if order_number in orders:
        # path = f"C:\\1C\\папка для заказов\\2024-11-06\\Набор. Альбом А5_озн_{order_number}_Новый"
        path = f"orders/Набор. Альбом А5_озн_{order_number}_Новый"
        quantity = orders[order_number]
        return {"result": True, "path": path, "quantity": quantity}
    else:
        return {"result": False, "info": f"The order by number {order_number} was not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)