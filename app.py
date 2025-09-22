import streamlit as st
from openai import OpenAI
import os
import json
import re
from typing import Optional

# ---- Init OpenAI client ----
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.set_page_config(page_title="Story → Image Prompts", layout="wide")
st.title("📖 Story → Image Prompt Generator (fix JSON)")

uploaded_file = st.file_uploader("📂 Tải lên file .txt chứa kịch bản", type=["txt"])

# ---- helper: gọi chat completion ----
def call_chat(user_prompt: str, system_prompt: Optional[str] = None, model: str = "gpt-4o-mini",
              temperature: float = 0.0, max_tokens: Optional[int] = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    kwargs = {"model": model, "messages": messages, "temperature": temperature}
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()

# ---- helper: cố gắng parse JSON, hoặc extract phần JSON ----
def try_parse_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        # Try to extract JSON array between first [ and last ]
        m = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

# ---- System prompts (strict) ----
SPLIT_SYSTEM = (
    "You are a tool that MUST output valid JSON only. "
    "Read the user's 'story' and split it into logical scenes. "
    "Return EXACTLY a JSON array (nothing else). Each element must be an object with keys: "
    "\"scene\" (integer, starting from 1), "
    "\"text\" (the scene's full original text), "
    "\"summary\" (a one-sentence Vietnamese summary). "
    "Do NOT include any extra commentary, markdown, or text. "
)

PROFILE_SYSTEM = (
    "You are a tool that extracts a character profile from a Vietnamese story. "
    "Return a short, plain text description (no JSON required) listing the main characters and "
    "their fixed attributes (gender, age range estimate, clothing, hairstyle, notable facial features) "
    "so the attributes can be reused exactly when generating image prompts. "
    "Keep it concise and avoid extra explanation."
)

PROMPT_GEN_SYSTEM = (
    "You are a tool that generates a single-line English image generation prompt (no JSON, no numbering, no quotes). "
    "Given the character profile and a scene's text, produce one clear, concise English prompt suitable for image models. "
    "Keep characters' attributes consistent with the profile. Output ONLY the English prompt string."
)

if uploaded_file:
    story_text = uploaded_file.read().decode("utf-8")
    st.subheader("📌 Văn bản gốc")
    st.text_area("Nội dung", story_text, height=250)

    if st.button("🚀 Phân tích & Sinh Prompt"):
        with st.spinner("Đang gọi GPT để trích xuất profile..."):
            try:
                character_profile = call_chat(story_text, system_prompt=PROFILE_SYSTEM, temperature=0.0)
            except Exception as e:
                st.error(f"Lỗi khi gọi API để tạo profile: {e}")
                st.stop()

        st.markdown("**Character profile (tóm tắt):**")
        st.code(character_profile)

        # --- Step 2: split into scenes (strict JSON expected) ---
        with st.spinner("Đang yêu cầu GPT chia đoạn (trả về JSON)..."):
            split_prompt = f"Story (Vietnamese):\n\n{story_text}"
            raw_split = ""
            try:
                raw_split = call_chat(split_prompt, system_prompt=SPLIT_SYSTEM, temperature=0.0, max_tokens=4000)
            except Exception as e:
                st.error(f"Lỗi gọi API chia đoạn: {e}")
                st.stop()

        scenes_list = try_parse_json(raw_split)

        # If parsing failed, try to ask GPT to reformat the previous output into valid JSON
        if scenes_list is None:
            st.warning("GPT trả về không đúng JSON. Mình sẽ cố gắng sửa (gọi GPT lần nữa để 'fix' JSON)...")
            with st.spinner("Yêu cầu GPT sửa JSON..."):
                fix_prompt = (
                    "The previous output (below) was supposed to be a JSON array describing scenes but is invalid.\n\n"
                    "Here is the invalid output:\n\n" + raw_split + "\n\n"
                    "Please correct it and RETURN ONLY a VALID JSON ARRAY in the format: "
                    '[{"scene": 1, "text": "...", "summary": "..."}, ...]. Nothing else.'
                )
                try:
                    fixed_raw = call_chat(fix_prompt, system_prompt="You are a JSON fixer. Output valid JSON only.", temperature=0.0, max_tokens=4000)
                    scenes_list = try_parse_json(fixed_raw)
                except Exception as e:
                    st.error(f"Lỗi khi cố gắng sửa JSON: {e}")
                    st.stop()

        if scenes_list is None:
            st.error("⚠️ Không thể chuyển kết quả của GPT thành JSON. Hiển thị raw output để debug.")
            st.subheader("Raw GPT output:")
            st.code(raw_split)
            st.stop()

        # Re-number scenes (ensure integer scene keys in order)
        for i, s in enumerate(scenes_list, start=1):
            s["scene"] = i

        st.success(f"Đã chia được {len(scenes_list)} cảnh.")
        st.subheader("📖 Các đoạn truyện đã chia")
        st.json(scenes_list)

        # --- Step 3: For each scene, generate English prompt (strict single-line) ---
        prompts = []
        with st.spinner("Đang sinh prompt ảnh cho từng cảnh..."):
            for s in scenes_list:
                scene_text = s.get("text", "")
                gen_input = f"Character profile:\n{character_profile}\n\nScene text (Vietnamese):\n{scene_text}\n\nProduce one concise English image prompt."
                try:
                    prompt_out = call_chat(gen_input, system_prompt=PROMPT_GEN_SYSTEM, temperature=0.0, max_tokens=512)
                except Exception as e:
                    st.error(f"Lỗi khi sinh prompt cho scene {s.get('scene')}: {e}")
                    prompt_out = ""
                prompts.append({"scene": s["scene"], "prompt": prompt_out})

        st.subheader("🎨 Prompt cho ảnh")
        st.json(prompts)

        # --- Prepare downloadable files ---
        story_txt = "\n\n".join([f"[{p['scene']}] {p['text']}" for p in scenes_list])
        prompts_txt = "\n\n".join([f"[{p['scene']}] {p['prompt']}" for p in prompts])

        st.download_button("⬇️ Tải story_segments.txt", data=story_txt, file_name="story_segments.txt", mime="text/plain")
        st.download_button("⬇️ Tải image_prompts.txt", data=prompts_txt, file_name="image_prompts.txt", mime="text/plain")

        # Also show raw outputs for debugging in expandable areas
        with st.expander("Raw split output (GPT)"):
            st.code(raw_split)
        with st.expander("Character profile (raw)"):
            st.code(character_profile)
