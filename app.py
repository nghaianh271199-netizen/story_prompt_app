import os
import json
import streamlit as st
from groq import Groq

# 🔑 Lấy API key từ biến môi trường
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    st.error("❌ Chưa có GROQ_API_KEY. Vào Settings > Secrets để thêm.")
    st.stop()

# 🚀 Tạo client Groq
client = Groq(api_key=groq_api_key)

# -------------------------
# GỌI GROQ
# -------------------------
def call_groq(prompt, model="llama-3.1-8b-instant", max_tokens=2000, force_json=False):
    try:
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        if force_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"❌ Lỗi GPT/Groq: {str(e)}")
        return None

# -------------------------
# UI
# -------------------------
st.title("📚 Story → Image Prompt Generator (Groq)")

uploaded_file = st.file_uploader("📂 Tải lên file kịch bản (.txt)", type=["txt"])

if uploaded_file:
    story_text = uploaded_file.read().decode("utf-8")

    if st.button("🔍 Phân tích & Sinh Prompt"):
        # -------------------------
        # Phân tích nhân vật
        # -------------------------
        with st.spinner("Đang phân tích nhân vật..."):
            profile_prompt = f"""
            Phân tích văn bản sau và liệt kê nhân vật chính.
            Trả về JSON **duy nhất**, không thêm chữ nào khác.

            Văn bản:
            {story_text[:3000]}

            Định dạng JSON:
            {{
              "characters": [
                {{
                  "name": "Tên nhân vật",
                  "description": "Mô tả ngoại hình + tính cách"
                }}
              ]
            }}
            """

            profile_text = call_groq(profile_prompt, model="llama-3.1-8b-instant", force_json=True)

            profile_json = {}
            characters = []

            if profile_text:
                try:
                    profile_json = json.loads(profile_text)
                    characters = profile_json.get("characters", [])
                except Exception:
                    st.error("⚠️ GPT trả về JSON không hợp lệ cho nhân vật.")
                    st.text(profile_text)
                    characters = []

        # Hiển thị danh sách nhân vật
        if characters:
            st.success("✅ Đã phân tích nhân vật:")
            for c in characters:
                st.write(f"- **{c['name']}**: {c['description']}")
        else:
            st.warning("⚠️ Không tìm thấy nhân vật, sẽ tiếp tục sinh prompt không có profile.")

        # -------------------------
        # Chia đoạn
        # -------------------------
        with st.spinner("Đang chia đoạn nội dung..."):
            split_prompt = f"""
            Hãy chia nội dung truyện sau thành các đoạn ngắn (mỗi đoạn ≤ 500 từ).
            Xuất JSON theo mẫu:
            {{
              "chunks": [
                {{"id": 1, "text": "Nội dung đoạn 1"}},
                {{"id": 2, "text": "Nội dung đoạn 2"}}
              ]
            }}
            Văn bản:
            {story_text[:8000]}
            """

            chunks_text = call_groq(split_prompt, model="llama-3.1-8b-instant", max_tokens=4000, force_json=True)

            chunks = []
            if chunks_text:
                try:
                    chunks_json = json.loads(chunks_text)
                    chunks = chunks_json.get("chunks", [])
                except Exception:
                    st.error("⚠️ GPT trả về JSON không hợp lệ cho chunks.")
                    st.text(chunks_text)
                    chunks = []
            else:
                st.error("❌ Không chia đoạn được.")

        # -------------------------
        # Sinh prompt cho từng đoạn
        # -------------------------
        prompts = []
        for ch in chunks:
            char_context = f"Nhân vật: {characters}" if characters else "Không có nhân vật cụ thể."
            scene_prompt = f"""
            Dựa trên đoạn truyện sau, hãy viết prompt để vẽ ảnh minh họa.
            {char_context}

            Đoạn:
            {ch['text']}

            Xuất JSON:
            {{
              "id": {ch['id']},
              "prompt": "Mô tả prompt ảnh"
            }}
            """
            scene_text = call_groq(scene_prompt, model="llama-3.1-8b-instant", max_tokens=1000, force_json=True)
            if scene_text:
                try:
                    scene_json = json.loads(scene_text)
                    prompts.append(scene_json)
                except Exception:
                    st.error(f"⚠️ GPT trả về JSON không hợp lệ cho đoạn {ch['id']}")
                    st.text(scene_text)

        # -------------------------
        # Xuất file kết quả
        # -------------------------
        if chunks and prompts:
            story_out = "\n\n".join([f"{c['id']}. {c['text']}" for c in chunks])
            prompt_out = "\n\n".join([f"{p['id']}. {p['prompt']}" for p in prompts])

            with open("story_chunks.txt", "w", encoding="utf-8") as f:
                f.write(story_out)

            with open("story_prompts.txt", "w", encoding="utf-8") as f:
                f.write(prompt_out)

            st.success("✅ Hoàn tất! Đã sinh file kết quả.")
            st.download_button("📥 Tải file story_chunks.txt", story_out, file_name="story_chunks.txt")
            st.download_button("📥 Tải file story_prompts.txt", prompt_out, file_name="story_prompts.txt")
