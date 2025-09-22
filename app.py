import streamlit as st
from openai import OpenAI
import os
import json

# ---- Setup API ----
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("📖 Story to Prompt Generator")

uploaded_file = st.file_uploader("📂 Tải lên file .txt chứa kịch bản", type=["txt"])

# ---- Hàm gọi GPT ----
def call_gpt(prompt, model="gpt-4o-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

if uploaded_file:
    story_text = uploaded_file.read().decode("utf-8")
    st.subheader("📌 Văn bản gốc:")
    st.text_area("Nội dung", story_text, height=200)

    if st.button("🚀 Phân tích & Sinh Prompt"):
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

        try:
            scenes_list = json.loads(scenes)
        except:
            st.error("⚠️ GPT trả về không đúng JSON. Vui lòng thử lại.")
            st.text(scenes)
            st.stop()

        # B3: Sinh prompt ảnh
        prompts = []
        for scene in scenes_list:
            prompt = f"""
            Nhân vật (giữ đồng nhất): {character_profile}.
            Đoạn truyện: {scene['text']}
            Viết prompt tiếng Anh để vẽ ảnh, giữ nhân vật đồng nhất, bối cảnh logic.
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
