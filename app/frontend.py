import streamlit as st
import requests

st.set_page_config(page_title="Simple Social", layout="wide")
API_URL = "http://127.0.0.1:8001"

if 'token' not in st.session_state: st.session_state.token = None
if 'user' not in st.session_state: st.session_state.user = None

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}

def login_page():
    st.title("🚀 Welcome")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        resp = requests.post(f"{API_URL}/auth/jwt/login", data={"username": email, "password": password})
        if resp.status_code == 200:
            st.session_state.token = resp.json()["access_token"]
            u_resp = requests.get(f"{API_URL}/users/me", headers=get_headers())
            st.session_state.user = u_resp.json()
            st.rerun()

def feed_page():
    st.title("🏠 Feed")
    resp = requests.get(f"{API_URL}/feed", headers=get_headers())
    if resp.status_code == 200:
        posts = resp.json().get("posts", [])
        for p in posts:
            with st.container():
                st.write(f"**{p['email']}**")
                if p['file_type'] == 'image': st.image(p['url'], width=400)
                else: st.video(p['url'])
                st.write(p['caption'])
                if p['is_owner'] and st.button("🗑️", key=p['id']):
                    requests.delete(f"{API_URL}/posts/{p['id']}", headers=get_headers())
                    st.rerun()
                st.divider()
    else: st.error(f"Failed to load feed: {resp.status_code}")

# Navigation logic
if st.session_state.user is None:
    login_page()
else:
    page = st.sidebar.radio("Menu", ["Feed", "Upload"])
    if st.sidebar.button("Logout"):
        st.session_state.user = st.session_state.token = None
        st.rerun()
    if page == "Feed": feed_page()
    else:
        st.title("📸 Upload")
        f = st.file_uploader("Select Media")
        c = st.text_input("Caption")
        if f and st.button("Post"):
            requests.post(f"{API_URL}/upload", files={"file": f}, data={"caption": c}, headers=get_headers())
            st.rerun()