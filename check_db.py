from database import SessionLocal, Order

def check_orders():
    db = SessionLocal()
    try:
        orders = db.query(Order).all()
        print(f"\n📊 FOUND {len(orders)} ORDERS IN POSTGRESQL:\n")
        for o in orders:
            print(f"✅ Order {o.order_id} | User: {o.user_id} | Item: {o.item_id} | Status: {o.status}")
    finally:
        db.close()

if __name__ == "__main__":
    check_orders()