import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from PIL import Image
import google.generativeai as genai
import io

# =================================================
# PAGE CONFIG (MUST BE FIRST)
# =================================================
st.set_page_config(
    page_title="🌿 Plant Disease Identifier",
    layout="centered"
)

# =================================================
# GEMINI CONFIG
# =================================================
genai.configure(api_key="AIzaSyAuffK7a_0VeayEMF6O5LL8H-fT2Z_nUO4")  # 🔴 ADD YOUR GEMINI API KEY
vision_model = genai.GenerativeModel("models/gemini-2.5-flash")

# =================================================
# DATABASE & AUTH FUNCTIONS
# =================================================
def get_db():
    return sqlite3.connect("users.db")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    # Auto-create admin
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("admin", hash_password("admin123"), "admin")
        )

    conn.commit()
    conn.close()

def register_user(username, password):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hash_password(password), "user")
        )
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role FROM users WHERE username=? AND password=?",
        (username, hash_password(password))
    )
    user = cur.fetchone()
    conn.close()
    return user

def get_all_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, role FROM users")
    users = cur.fetchall()
    conn.close()
    return users

# =================================================
# INIT DB
# =================================================
init_db()

# =================================================
# SESSION STATE
# =================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# =================================================
# 🔐 AUTH UI
# =================================================
if not st.session_state.logged_in:

    st.title("🔐 Login / Register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login_user(u, p)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = user[0]
                st.session_state.role = user[1]
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        nu = st.text_input("New Username")
        np = st.text_input("New Password", type="password")
        if st.button("Register"):
            if register_user(nu, np):
                st.success("Registration successful! Login now.")
            else:
                st.error("Username already exists")

# =================================================
# 🌿 MAIN APP (AFTER LOGIN)
# =================================================
else:

    # ---------------- SIDEBAR ----------------
    st.sidebar.success(f"👤 {st.session_state.username}")
    st.sidebar.write(f"Role: **{st.session_state.role}**")

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # ---------------- ADMIN PANEL ----------------
    if st.session_state.role == "admin":
        st.sidebar.markdown("### 👑 Admin Panel")
        if st.sidebar.button("View Registered Users"):
            users = get_all_users()
            df = pd.DataFrame(users, columns=["ID", "Username", "Role"])
            st.subheader("📋 Registered Users")
            st.dataframe(df)

    # =================================================
    # 🌿 PLANT DISEASE IDENTIFIER
    # =================================================
    st.title("🌿 Plant Disease Identifier (Gemini Vision)")
    st.markdown(
        "Upload a **plant leaf image** to identify disease, treatment, and prevention steps."
    )

    uploaded_image = st.file_uploader(
        "Upload Leaf Image (JPG / PNG)",
        type=["jpg", "jpeg", "png"]
    )

    def get_diagnosis(image):
        prompt = """
You are a plant pathologist.

1. Identify the plant and disease (if any).
2. Suggest treatment steps.
3. Give preventive measures.
4. Recommend organic or chemical remedies.

Respond clearly.
"""
        img = image.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)

        response = vision_model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": buf.read()}
        ])
        return response.text.strip()

    if uploaded_image:
        image = Image.open(uploaded_image)
        image.thumbnail((400, 400))
        st.image(image, caption="Uploaded Leaf Image")

        if st.button("🔍 Diagnose Disease"):
            with st.spinner("Analyzing image using Gemini Vision..."):
                try:
                    result = get_diagnosis(image)
                    st.subheader("🧪 Diagnosis Result")
                    st.text_area(
                        "AI Diagnosis",
                        value=result,
                        height=350
                    )
                except Exception as e:
                    st.error(f"Gemini Error: {e}")
