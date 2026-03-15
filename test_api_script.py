import os
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def create_test_pdf():
    from reportlab.pdfgen.canvas import Canvas
    c = Canvas("test.pdf")
    c.drawString(100, 100, "This is a test sentence. Let's see if it works.")
    c.save()

def run_test():
    create_test_pdf()
    with open("test.pdf", "rb") as f:
        # Note: name of the field is "file"
        response = client.post("/api/detect-file", files={"file": ("test.pdf", f, "application/pdf")})
        print(f"Status Code: {response.status_code}")
        try:
            print(f"Response JSON: {response.json()}")
        except Exception as e:
            print(f"Failed to decode JSON: {response.text}")

if __name__ == "__main__":
    run_test()
