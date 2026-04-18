from locust import HttpUser, task, between
import random
import uuid

class Shopper(HttpUser):
    # Each fake user will wait between 1 and 3 seconds before clicking checkout again
    wait_time = between(1, 3)

    @task
    def buy_item(self):
        # Randomly pick an item to buy
        items = ["mechanical_keyboard", "playstation_5", "coffee_mug", "desk_mat"]
        item = random.choice(items)
        
        # Build the exact JSON payload our FastAPI endpoint expects
        payload = {
            "user_id": f"load_test_user_{uuid.uuid4().hex[:8]}",
            "item_id": item,
            "quantity": 1
        }

        # Hit the /checkout endpoint
        self.client.post("/checkout", json=payload)