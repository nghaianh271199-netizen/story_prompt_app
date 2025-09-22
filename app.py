import os
import json
import streamlit as st
from groq import Groq

# 🔑 Lấy API key từ biến môi trường
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ==========================
# HÀM GỌI GPT/GROQ
# ==========================
def call_gpt(prompt, model="llama-3.1-8b-instant", temperature=0.7):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Lỗi GPT/Groq: {e}")
        return None


# ==========================
# GIAO DIỆN STREAMLIT
# ==========================
st.title("📚 Story to Image Prompt Generator (Groq API)")

uploaded_file = st.file_uploader("📂 Tải file kịch bản (.txt)", type="txt")

if uploaded_file:
    story_text = uploaded_file.read().decode("utf-8")

    if st.button("🚀 Phân tích và sinh prompt"):
        st.info("⏳ Đang phân tích nội dung...")

        # --------------------------
        # BƯỚC 1: TÓM TẮT NHÂN VẬT
        # --------------------------
        profile_prompt = f"""
        Hãy phân tích đoạn truyện sau và rút ra hồ sơ nhân vật chính:
        - Tên, giới tính, độ tuổi
        - Ngoại hình, trang phục, tính cách
        - Mối quan hệ chính
        Chỉ trả về JSON hợp lệ theo format sau:
        {{
            "characters": [
                {{
                    "name": "Tên nhân vật",
                    "description": "Mô tả chi tiết"
                }}
            ]
        }}
        Văn bản:
        {story_text}
        """

        character_profile = call_gpt(profile_prompt, model="llama-3.1-8b-instant")

        try:
            characters = json.loads(character_profile)
        except:
            st.error("⚠️ GPT trả về JSON không hợp lệ cho nhân vật.")
            st.stop()

        st.success("✅ Hồ sơ nhân vật đã phân tích xong.")

        # --------------------------
        # BƯỚC 2: CHIA TRUYỆN THÀNH ĐOẠN
        # --------------------------
        split_prompt = f"""
        Hãy chia câu chuyện sau thành các đoạn ngắn, mỗi đoạn là một cảnh.
        Trả về JSON hợp lệ:
        {{
            "scenes": [
                {{
                    "id": 1,
                    "text": "Nội dung đoạn 1"
                }},
                {{
                    "id": 2,
                    "text": "Nội dung đoạn 2"
                }}
            ]
        }}
        Văn bản:
        {story_text}
        """

        split_result = call_gpt(split_prompt, model="llama-3.1-8b-instant")

        try:
            scenes = json.loads(split_result)["scenes"]
        except:
            st.error("⚠️ GPT trả về JSON không hợp lệ khi chia đoạn.")
            st.stop()

        st.success("✅ Đã chia kịch bản thành các đoạn nhỏ.")

        # --------------------------
        # BƯỚC 3: TẠO PROMPT CHO TỪNG ĐOẠN
        # --------------------------
        output_story = []
        output_prompts = []

        for scene in scenes:
            prompt_prompt = f"""
            Hãy viết prompt tạo ảnh cho cảnh dưới đây.
            Yêu cầu:
            - Bối cảnh phải logic
            - Nhân vật đồng nhất với hồ sơ sau: {json.dumps(characters, ensure_ascii=False)}
            - Trả về đúng JSON:
            {{
                "id": {scene["id"]},
                "prompt": "Mô tả chi tiết cho AI vẽ ảnh"
            }}
            
            Cảnh: {scene["text"]}
            """

            out = call_gpt(prompt_prompt, model="llama-3.1-70b-versatile")

            try:
                parsed = json.loads(out)
                output_story.append(f"{scene['id']}. {scene['text']}")
                output_prompts.append(f"{parsed['id']}. {parsed['prompt']}")
            except:
                st.warning(f"⚠️ JSON không hợp lệ ở đoạn {scene['id']}, bỏ qua.")

        # --------------------------
        # BƯỚC 4: XUẤT FILE KẾT QUẢ
        # --------------------------
        with open("story_scenes.txt", "w", encoding="utf-8") as f:
            f.write("\n\n".join(output_story))

        with open("story_prompts.txt", "w", encoding="utf-8") as f:
            f.write("\n\n".join(output_prompts))

        st.success("🎉 Hoàn tất! Bạn có thể tải file kết quả bên dưới:")

        st.download_button("⬇️ Tải file đoạn truyện", data="\n\n".join(output_story),
                           file_name="story_scenes.txt")

        st.download_button("⬇️ Tải file prompts", data="\n\n".join(output_prompts),
                           file_name="story_prompts.txt")
