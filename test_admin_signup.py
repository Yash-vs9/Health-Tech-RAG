import sys
import os

# Add the project root to the python path
sys.path.insert(0, "/Users/yash/Desktop/RAG")

from backend.db.supabase_client import get_admin_client, get_anon_client

def test_admin_signup():
    admin = get_admin_client()
    anon = get_anon_client()
    email = "admin_test@yash.com"
    password = "password123"
    try:
        res = admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": "Admin Test"}
        })
        print("Admin Create User:", res)
        
        res2 = anon.auth.sign_in_with_password({"email": email, "password": password})
        print("Login after create:", res2.session is not None)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("/Users/yash/Desktop/RAG/backend/.env")
    test_admin_signup()
