import redis

def seed_inventory():
    # Connect to our local Redis Docker container
    r = redis.Redis(host='127.0.0.1', port=6379, decode_responses=True)
    
    # Let's say we only have 5 mechanical keyboards in stock
    r.set("inventory:mechanical_keyboard", 5)
    r.set("inventory:playstation_5", 2)
    
    print("✅ Redis Inventory Seeded!")
    print(f"Mechanical Keyboards: {r.get('inventory:mechanical_keyboard')}")
    print(f"PlayStation 5s: {r.get('inventory:playstation_5')}")

if __name__ == "__main__":
    seed_inventory()
    