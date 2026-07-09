import sys
import os

# Add the project root to the python path
sys.path.insert(0, "/Users/yash/Desktop/RAG")

from backend.db.supabase_client import get_anon_client

def test_auth():
    client = get_anon_client()
    email = "test4@yash.com"
    password = "password123"
    try:
        res = client.auth.sign_up({"email": email, "password": password})
        print("Signup:", res)
    except Exception as e:
        print("Signup failed:", e)

    try:
        res2 = client.auth.sign_in_with_password({"email": email, "password": password})
        print("Login:", res2)
    except Exception as e:
        print("Login failed:", e)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("/Users/yash/Desktop/RAG/backend/.env")
    test_auth()
