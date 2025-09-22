import streamlit as st
from openai import OpenAI
import re
import os

# Cấu hình giao diện
st.set_page_config(page_title="Chia truyện & Sinh Prompt", layout="wide")
st.title("📖 Chia truyện & Sinh Prompt minh hoạ")

# Lấy API Key từ biến môi trường (khuyến nghị) hoặc nhập trực tiếp
api_key = os.getenv("OPENAI_API_KEY") or st.text_input("🔑 Nhập API Key OpenAI của bạn", type="password")

# Nhập truyện trực tiếp
story_text = st.text_area("✍ Nhập truyện trực tiếp vào đây", height=400)

if story_text and api_key:
    client = OpenAI(api_key=api_key)

    if st.button("🚀 Xử lý truyện"):
        with st.spinner("Đang phân tích và tạo prompt..."):
            # Gọi GPT chia đoạn & sinh prompt
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "Bạn là công cụ chia truyện thành các đoạn theo mạch ngữ nghĩa."},
                    {"role": "user", "content": f"""
Hãy chia văn bản sau thành các đoạn theo mạch truyện.
Với mỗi đoạn:
1. Giữ nguyên văn bản gốc, chỉ cắt đoạn hợp lý.
2. Tạo prompt minh hoạ cảnh cho đoạn đó.
Lưu ý:
- Nhân vật phải đồng nhất từ đầu đến cuối (tên, ngoại hình).
- Bối cảnh logic theo diễn biến truyện.
- Xuất kết quả theo dạng:

[Đoạn 1]
<Nội dung đoạn>

[Prompt 1]
<Mô tả prompt>

[Đoạn 2]
<Nội dung đoạn>

[Prompt 2]
<Mô tả prompt>
...

Văn bản:
{story_text}
"""}
                ],
                temperature=0.7
            )

            result = response.choices[0].message.content

            # Tách đoạn và prompt bằng regex
            doan_truyen = []
            prompt_list = []

            matches = re.findall(r"\[Đoạn (\d+)\]\s*(.*?)\s*\[Prompt \1\]\s*(.*?)(?=\n\[|$)", result, re.S)
            for m in matches:
                idx, doan, prompt = m
                doan_truyen.append(f"Đoạn {idx}\n{doan.strip()}\n")
                prompt_list.append(f"Prompt {idx}\n{prompt.strip()}\n")

            if doan_truyen:
                doan_text = "\n".join(doan_truyen)
                prompt_text = "\n".join(prompt_list)

                st.subheader("📑 Kết quả")
                col1, col2 = st.columns(2)
                with col1:
                    st.text_area("Đoạn truyện", doan_text, height=400)
                with col2:
                    st.text_area("Prompt", prompt_text, height=400)

                # Nút tải file
                st.download_button("⬇️ Tải file Đoạn truyện", data=doan_text, file_name="doan_truyen.txt")
                st.download_button("⬇️ Tải file Prompt", data=prompt_text, file_name="prompt.txt")
            else:
                st.error("❌ Không tách được đoạn và prompt. Hãy kiểm tra lại.")
