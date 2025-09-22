import streamlit as st
from openai import OpenAI
import os, json, re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("📖 Story → Prompts")

uploaded_file = st.file_uploader("📂 Upload .txt", type=["txt"])

def call_chat(prompt, system="", model="gpt-4o-mini", temperature=0):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
    return resp.choices[0].message.content.strip()

def try_parse_json(raw: str):
    try:
        return json.loads(raw)
    except:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except:
                return None
        return None

if uploaded_file:
    story_text = uploaded_file.read().decode("utf-8")

    if st.button("🚀 Chia đoạn & Sinh prompt"):
        # 1) Profile nhân vật
        profile = call_chat(
            f"Phân tích nhân vật chính trong truyện:\n{story_text}",
            system="Trả về mô tả ngắn gọn về nhân vật và đặc điểm cố định."
        )

        # 2) Chia đoạn (JSON)
        split_raw = call_chat(
            f"Chia văn bản sau thành các cảnh nhỏ, output JSON: "
            f'[{{"scene":1,"text":"...","summary":"..."}}]\n\n{story_text}',
            system="Bạn phải trả về JSON hợp lệ, không thêm giải thích."
        )
        scenes = try_parse_json(split_raw)

        if not scenes:
            st.error("⚠ GPT không trả JSON hợp lệ.")
            st.stop()

        # 3) Sinh prompt cho từng đoạn
        prompts = []
        for s in scenes:
            pr = call_chat(
                f"Profile: {profile}\n\nĐoạn: {s['text']}\n\n"
                "Viết prompt tiếng Anh để vẽ ảnh, giữ nhân vật đồng nhất."
            )
            prompts.append({"scene": s["scene"], "prompt": pr})

        # 4) Tạo nội dung file
        story_txt = "\n\n".join([f"[{s['scene']}] {s['text']}" for s in scenes])
        prompt_txt = "\n\n".join([f"[{p['scene']}] {p['prompt']}" for p in prompts])

        # 5) Nút tải file
        st.download_button("⬇️ Tải story_segments.txt", story_txt, "story_segments.txt")
        st.download_button("⬇️ Tải image_prompts.txt", prompt_txt, "image_prompts.txt")

        # Hiển thị preview
        st.subheader("📖 Đoạn truyện đã chia")
        st.json(scenes)
        st.subheader("🎨 Prompt ảnh")
        st.json(prompts)
