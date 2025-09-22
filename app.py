import streamlit as st
import google.generativeai as genai

# ==============================
# Cấu hình Gemini API
# ==============================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Khởi tạo model Gemini
model = genai.GenerativeModel("gemini-1.5-flash")

# ==============================
# Giao diện Streamlit
# ==============================
st.set_page_config(page_title="Story Prompt App", page_icon="✨")
st.title("✨ Ứng dụng sinh Prompt với Gemini")

# Nhập nội dung
text_input = st.text_area("✍️ Nhập nội dung truyện hoặc đoạn văn:")

# Xử lý khi bấm nút
if st.button("🚀 Phân tích và sinh Prompt"):
    if not text_input.strip():
        st.warning("⚠️ Vui lòng nhập nội dung trước khi chạy.")
    else:
        with st.spinner("⏳ Đang phân tích và tạo prompt..."):
            try:
                prompt = f"""
                Bạn là công cụ chuyên phân tích văn bản để sinh prompt.
                Hãy phân tích đoạn văn sau và xuất ra **JSON hợp lệ** với cấu trúc:
                {{
                  "summary": "Tóm tắt ngắn gọn",
                  "characters": ["nhân vật 1", "nhân vật 2"],
                  "prompts": ["prompt gợi ý 1", "prompt gợi ý 2"]
                }}

                Văn bản: {text_input}
                """

                response = model.generate_content(prompt)

                # Hiển thị kết quả
                st.subheader("📌 Kết quả JSON:")
                st.json(response.text)

            except Exception as e:
                st.error(f"❌ Lỗi: {e}")
