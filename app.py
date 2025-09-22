# app.py
import os
import streamlit as st
from openai import OpenAI

# Lấy API Key từ Secret trên Streamlit Cloud
api_key = os.getenv("OPENAI_API_KEY")

# Nếu chưa cấu hình, thông báo lỗi và dừng app
if not api_key:
    st.error("Chưa cấu hình OPENAI_API_KEY trong biến môi trường!")
    st.stop()

# Khởi tạo client OpenAI
client = OpenAI(api_key=api_key)

# Giao diện Streamlit
st.title("Demo ChatGPT với Biến Môi Trường")

st.write("""
Ứng dụng này sử dụng **OpenAI API** mà không yêu cầu nhập API Key.
Key được lấy từ **Secrets** trên Streamlit Cloud.
""")

# Nhập câu hỏi từ người dùng
user_input = st.text_input("Nhập câu hỏi của bạn:")

# Khi bấm nút gửi
if st.button("Gửi"):
    if user_input.strip() == "":
        st.warning("Vui lòng nhập câu hỏi!")
    else:
        try:
            # Gọi OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": user_input}]
            )
            # Hiển thị kết quả
            answer = response.choices[0].message.content
            st.success(answer)
        except Exception as e:
            st.error(f"Lỗi khi gọi OpenAI API: {e}")
