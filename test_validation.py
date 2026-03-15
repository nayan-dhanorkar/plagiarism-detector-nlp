import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
import numpy as np

app = FastAPI()

class Item(BaseModel):
    score: float

@app.get("/test", response_model=Item)
def test():
    # Return a numpy float which Pydantic might reject
    return {"score": np.float32(1.5)}

client = TestClient(app)

def run():
    response = client.get("/test")
    print(response.status_code)
    print(response.json())

if __name__ == "__main__":
    run()
