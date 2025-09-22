import streamlit as st
import openai
import os
import json

# Lấy API Key từ môi trường (Secrets trên Streamlit Cloud)
openai.api_key = os.getenv("OPENAI_API_KEY")

st.title("📖 Story to Prompt Generator")

uploaded_file = st.file_uploader("Tải lên file .txt chứa kịch bản", type=["txt"])

def call_gpt(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response["choices"][0]["message"]["content"]

if uploaded_file:
    story_text = uploaded_file.read().decode("utf-8")
    st.subheader("📌 Văn bản gốc:")
    st.text_area("Nội dung", story_text, height=200)

    if st.button("Phân tích & Sinh Prompt"):
        # B1: Tạo profile nhân vật
        profile_prompt = f"""
        Đọc toàn bộ văn bản sau và trích xuất hồ sơ nhân vật (Character Profile).
        Ghi rõ tên, giới tính, trang phục, đặc điểm cố định.
        Văn bản: {story_text}
        """
        character_profile = call_gpt(profile_prompt)

        # B2: Chia đoạn
        split_prompt = f"""
        Dựa trên văn bản sau, hãy chia thành các cảnh nhỏ hợp lý theo ngữ cảnh.
        Trả về kết quả dạng JSON: [{{"scene": 1, "text": "...", "summary": "..."}}]
        Văn bản: {story_text}
        """
        scenes = call_gpt(split_prompt)
        scenes_list = json.loads(scenes)

        # B3: Sinh prompt ảnh
        prompts = []
        for scene in scenes_list:
            prompt = f"""
            Nhân vật: {character_profile}.
            Đoạn truyện: {scene['text']}
            Viết prompt tiếng Anh để vẽ ảnh, giữ nhân vật đồng nhất.
            """
            prompt_out = call_gpt(prompt)
            prompts.append({"scene": scene["scene"], "prompt": prompt_out})

        # Hiển thị kết quả
        st.subheader("📖 Các đoạn truyện")
        st.json(scenes_list)
        st.subheader("🎨 Prompt cho ảnh")
        st.json(prompts)

        # Xuất file
        with open("story_segments.txt", "w", encoding="utf-8") as f1, \
             open("image_prompts.txt", "w", encoding="utf-8") as f2:
            for scene in scenes_list:
                f1.write(f"[{scene['scene']}] {scene['text']}\n")
            for p in prompts:
                f2.write(f"[{p['scene']}] {p['prompt']}\n")

        st.success("✅ Đã tạo file story_segments.txt và image_prompts.txt")
