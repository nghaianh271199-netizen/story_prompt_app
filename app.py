import streamlit as st
import openai
import os
import json

# Lấy API key từ biến môi trường
openai.api_key = os.getenv("OPENAI_API_KEY")

# Hàm gọi GPT và luôn cố gắng trả JSON hợp lệ
def call_gpt(prompt, model="gpt-4o-mini", temperature=0.7):
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        content = response.choices[0].message.content.strip()

        # Nếu GPT trả về không phải JSON thì thử "sửa" bằng cách ép chuỗi
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            fix_prompt = f"""Nội dung sau không phải JSON hợp lệ. 
            Hãy chuyển nó thành JSON đúng cú pháp, chỉ trả về JSON thôi:
            {content}"""
            fix_response = openai.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": fix_prompt}],
                temperature=0
            )
            fixed_content = fix_response.choices[0].message.content.strip()
            return json.loads(fixed_content)

    except Exception as e:
        st.error(f"Lỗi GPT: {e}")
        return None

# Giao diện Streamlit
st.title("📖 Story to Prompt Generator")

uploaded_file = st.file_uploader("Tải lên file kịch bản (.txt)", type=["txt"])

if uploaded_file is not None:
    story_text = uploaded_file.read().decode("utf-8")

    if st.button("Phân tích và sinh prompt"):
        with st.spinner("Đang phân tích câu chuyện..."):
            split_prompt = f"""
            Bạn là một trợ lý sáng tạo. 
            Nhiệm vụ: chia nội dung dưới đây thành các đoạn nhỏ logic theo ngữ cảnh,
            và tạo prompt để sinh ảnh cho từng đoạn.
            Yêu cầu:
            - Các nhân vật phải đồng nhất từ đầu đến cuối.
            - Bối cảnh hợp lý, không mâu thuẫn.
            - Xuất JSON dạng:
            {{
              "segments": [
                {{"id": 1, "text": "đoạn truyện", "prompt": "prompt sinh ảnh"}},
                {{"id": 2, "text": "đoạn truyện", "prompt": "prompt sinh ảnh"}}
              ]
            }}

            Văn bản:
            {story_text}
            """

            result = call_gpt(split_prompt)

            if result:
                st.success("✅ Đã phân tích thành công!")

                # Hiển thị kết quả
                for seg in result.get("segments", []):
                    st.subheader(f"Đoạn {seg['id']}")
                    st.write(seg["text"])
                    st.code(seg["prompt"], language="markdown")

                # Xuất file
                with open("story_segments.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                with open("story_segments.txt", "w", encoding="utf-8") as f:
                    for seg in result.get("segments", []):
                        f.write(f"Đoạn {seg['id']}:\n{seg['text']}\nPrompt: {seg['prompt']}\n\n")

                st.download_button("⬇️ Tải JSON", data=json.dumps(result, ensure_ascii=False, indent=2), file_name="story_segments.json")
                st.download_button("⬇️ Tải TXT", data=open("story_segments.txt", "r", encoding="utf-8").read(), file_name="story_segments.txt")
