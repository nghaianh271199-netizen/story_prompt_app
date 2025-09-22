import streamlit as st
from groq import Groq
import os
import json

# Khởi tạo client Groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def call_gpt(prompt, model="llama3-70b-8192", temperature=0.7):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        st.error(f"Lỗi GPT/Groq: {e}")
        return None

st.title("📖 Story to Prompt Generator (Groq)")

uploaded_file = st.file_uploader("Tải lên file kịch bản (.txt)", type=["txt"])

if uploaded_file is not None:
    story_text = uploaded_file.read().decode("utf-8")

    if st.button("Phân tích và sinh prompt"):
        with st.spinner("Đang phân tích câu chuyện..."):

            # -------- BƯỚC 1: Chia đoạn với model nhỏ (llama3-8b) --------
            split_prompt = f"""
            Hãy chia nội dung dưới đây thành các đoạn nhỏ hợp lý theo ngữ cảnh.
            Chỉ cần xuất JSON:
            {{
              "segments": [
                {{"id": 1, "text": "..." }},
                {{"id": 2, "text": "..." }}
              ]
            }}

            Văn bản:
            {story_text}
            """

            split_result = call_gpt(split_prompt, model="llama3-8b-8192")

            if not split_result:
                st.error("❌ Không chia đoạn được.")
            else:
                try:
                    segments = json.loads(split_result)["segments"]
                except:
                    st.error("JSON chia đoạn không hợp lệ.")
                    segments = []

                # -------- BƯỚC 2: Sinh prompt cho từng đoạn bằng model mạnh (llama3-70b) --------
                results = {"segments": []}
                for seg in segments:
                    prompt_prompt = f"""
                    Đây là một đoạn truyện:
                    {seg['text']}

                    Nhiệm vụ: viết prompt để sinh ảnh minh họa đoạn này.
                    Yêu cầu:
                    - Nhân vật đồng nhất với các đoạn khác
                    - Bối cảnh hợp lý, logic
                    - Viết prompt ngắn gọn, dễ hiểu

                    Xuất JSON:
                    {{
                      "id": {seg['id']},
                      "text": "{seg['text']}",
                      "prompt": "..."
                    }}
                    """
                    out = call_gpt(prompt_prompt, model="llama3-70b-8192")
                    try:
                        obj = json.loads(out)
                        results["segments"].append(obj)
                    except:
                        results["segments"].append({
                            "id": seg["id"],
                            "text": seg["text"],
                            "prompt": out
                        })

                st.success("✅ Hoàn tất phân tích và sinh prompt!")

                for seg in results["segments"]:
                    st.subheader(f"Đoạn {seg['id']}")
                    st.write(seg["text"])
                    st.code(seg["prompt"], language="markdown")

                # Xuất file JSON
                json_str = json.dumps(results, ensure_ascii=False, indent=2)
                st.download_button("⬇️ Tải JSON", data=json_str, file_name="story_segments.json")

                # Xuất file TXT
                txt_out = ""
                for seg in results["segments"]:
                    txt_out += f"Đoạn {seg['id']}:\n{seg['text']}\nPrompt: {seg['prompt']}\n\n"
                st.download_button("⬇️ Tải TXT", data=txt_out, file_name="story_segments.txt")
