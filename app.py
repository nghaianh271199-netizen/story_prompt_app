import os
import re
import time
import json
import streamlit as st
from groq import Groq
from typing import List, Optional

# -----------------------
# Config
# -----------------------
GROQ_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_KEY:
    st.error("GROQ_API_KEY chưa được set trong Secrets. Vui lòng thêm key rồi redeploy.")
    st.stop()

client = Groq(api_key=GROQ_KEY)

# Chunking params (tùy chỉnh trên UI nếu muốn)
DEFAULT_MAX_CHUNK_CHARS = 6000   # ~ an toàn; sửa giảm nếu vẫn bị lỗi
DEFAULT_OVERLAP_CHARS = 200
PAUSE_BETWEEN_CALLS = 0.6        # giãn request để giảm TPM pressure

# -----------------------
# Helpers
# -----------------------
def try_parse_json(raw: str):
    """Try to parse JSON or extract array between [ ... ]."""
    try:
        return json.loads(raw)
    except Exception:
        m = re.search(r"\[.*\]", raw, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        # try object form {"scenes": [...]}
        m2 = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m2:
            try:
                return json.loads(m2.group(0))
            except Exception:
                return None
        return None

def fix_json_with_model(raw_output: str, model="llama-3.1-8b-instant") -> Optional[str]:
    """Ask model to return valid JSON only from a previous raw output."""
    prompt = (
        "The text below was supposed to be valid JSON but is not. "
        "Please CORRECT it and RETURN ONLY VALID JSON (no explanation).\n\n"
        f"Invalid output:\n{raw_output}\n\n"
        "Return only the corrected JSON."
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=0.0
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"Không thể sửa JSON tự động: {e}")
        return None

def chunk_text_by_paragraphs(text: str, max_chars=DEFAULT_MAX_CHUNK_CHARS, overlap=DEFAULT_OVERLAP_CHARS) -> List[str]:
    """Split by paragraphs and aggregate to chunks <= max_chars. Add small overlap."""
    paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = []
    current = ""
    for p in paras:
        if len(current) + len(p) + 2 <= max_chars:
            current = (current + "\n\n" + p).strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk with overlap from previous tail if possible
            tail = (chunks[-1][-overlap:] if chunks else "")
            current = (tail + "\n\n" + p).strip()
    if current:
        chunks.append(current)
    return chunks

def call_groq(prompt: str, model: str, temperature: float = 0.0) -> Optional[str]:
    """Call Groq and return raw content or show error info."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=temperature
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # present clearer message for common errors
        msg = str(e)
        if "413" in msg or "Request too large" in msg:
            st.error("Error: Request too large for model. Giảm kích thước chunk (max_chars) hoặc dùng model nhẹ hơn.")
        elif "429" in msg:
            st.error("Rate limit / quota error from Groq: " + msg)
        else:
            st.error(f"Groq API error: {msg}")
        return None

# -----------------------
# Streamlit UI
# -----------------------
st.title("Story → Image Prompts (Groq + chunking)")

st.markdown(
    "Uploads a long `.txt` story, automatically chunks it to avoid oversized requests, "
    "splits into scenes and generates English prompts for each scene."
)

uploaded = st.file_uploader("Tải lên file .txt", type=["txt"])
max_chars = st.number_input("Max characters per chunk (giảm nếu vẫn bị lỗi)", min_value=1000, max_value=20000, value=DEFAULT_MAX_CHUNK_CHARS, step=500)
overlap = st.number_input("Overlap characters between chunks", min_value=0, max_value=2000, value=DEFAULT_OVERLAP_CHARS, step=50)
use_profile_refine = st.checkbox("Refine character profile by scanning more chunks (tốn nhiều request hơn)", value=False)

if uploaded:
    text = uploaded.read().decode("utf-8")
    st.info(f"Nội dung đã tải: {len(text)} ký tự")
    if st.button("Phân tích & Sinh prompt (stream-safe)"):
        chunks = chunk_text_by_paragraphs(text, max_chars=max_chars, overlap=overlap)
        st.write(f"Số chunk tạo được: {len(chunks)} (max_chars={max_chars})")

        # 1) CREATE CHARACTER PROFILE from first N chunks (default 2)
        sample_chunks = chunks[:2] if len(chunks) >= 2 else chunks
        sample_text = "\n\n".join(sample_chunks)
        profile_prompt = (
            "Extract the CHARACTER PROFILE from the Vietnamese story fragment below. "
            "Return ONLY valid JSON with key 'characters' which is a list of objects "
            "like {\"name\": \"Tên\", \"description\": \"short Vietnamese description\"}.\n\n"
            f"Text:\n{sample_text}\n\n"
            "Output JSON only."
        )
        raw_profile = call_groq(profile_prompt, model="llama-3.1-8b-instant", temperature=0.0)
        if not raw_profile:
            st.error("Không nhận được profile từ Groq.")
            st.stop()

        profile_json = try_parse_json(raw_profile)
        if profile_json is None:
            fixed = fix_json_with_model(raw_profile, model="llama-3.1-8b-instant")
            profile_json = try_parse_json(fixed) if fixed else None

        if profile_json is None:
            st.warning("Không thể phân tích chính xác hồ sơ nhân vật. Sẽ tiếp tục nhưng nhân vật có thể không đồng nhất.")
            characters = []
        else:
            characters = profile_json.get("characters", [])
            st.success(f"Đã trích xuất {len(characters)} nhân vật (từ sample chunks).")
            st.json(characters)

        # 2) Split each chunk into scenes (and avoid duplicates using previous summaries)
        scenes = []
        previous_summaries = []  # keep short summaries to avoid duplication
        for i, chunk in enumerate(chunks, start=1):
            st.write(f"Processing chunk {i}/{len(chunks)} ...")
            split_prompt = (
                "Split the following Vietnamese text into logical scenes (each is a short self-contained scene). "
                "Return ONLY a JSON array of objects with keys: \"text\" (the full scene text) and \"summary\" (one-sentence Vietnamese summary). "
                "Do NOT include any extra commentary.\n\n"
                f"Previous scene summaries (avoid duplicating these):\n{json.dumps(previous_summaries, ensure_ascii=False)}\n\n"
                f"Chunk text:\n{chunk}\n\n"
                "Output JSON array only."
            )
            raw = call_groq(split_prompt, model="llama-3.1-8b-instant", temperature=0.0)
            if raw is None:
                st.error(f"Chunk {i}: lỗi API, dừng.")
                st.stop()

            parsed = try_parse_json(raw)
            if parsed is None:
                fixed_raw = fix_json_with_model(raw, model="llama-3.1-8b-instant")
                parsed = try_parse_json(fixed_raw) if fixed_raw else None

            if parsed is None:
                st.warning(f"Chunk {i}: GPT trả về không parse được JSON. Hiển thị raw để debug.")
                st.code(raw)
                # skip this chunk to be safe
                time.sleep(PAUSE_BETWEEN_CALLS)
                continue

            # parsed should be a list of scenes or an object containing scenes
            if isinstance(parsed, dict) and "scenes" in parsed:
                parsed_list = parsed["scenes"]
            elif isinstance(parsed, list):
                parsed_list = parsed
            else:
                st.warning(f"Chunk {i}: Unexpected JSON shape; skip.")
                time.sleep(PAUSE_BETWEEN_CALLS)
                continue

            # append unique scenes (by summary substring)
            for item in parsed_list:
                summary = (item.get("summary") or "")[:200].strip()
                text_scene = item.get("text") or item.get("scene") or ""
                # dedup simple: if summary substring already present, skip
                if any(summary and (summary in prev or prev in summary) for prev in previous_summaries):
                    continue
                scenes.append({"text": text_scene.strip(), "summary": summary})
                previous_summaries.append(summary)
                # keep previous_summaries bounded
                if len(previous_summaries) > 50:
                    previous_summaries = previous_summaries[-50:]

            time.sleep(PAUSE_BETWEEN_CALLS)

        if not scenes:
            st.error("Không tạo được cảnh nào. Kiểm tra input hoặc giảm max_chars.")
            st.stop()

        st.success(f"Tổng số cảnh sau khi gộp: {len(scenes)}")
        # show first few scenes
        for idx, s in enumerate(scenes[:6], start=1):
            st.markdown(f"**[{idx}]** {s['summary']}")
            st.write(s['text'][:400].replace("\n", " ") + ("..." if len(s['text'])>400 else ""))

        # Optional: refine profile scanning more chunks (if user ticked)
        if use_profile_refine and len(chunks) > 2:
            st.info("Refining character profile by scanning more chunks...")
            more_text = "\n\n".join(chunks[:min(6, len(chunks))])
            refine_prompt = (
                "Given the parsed characters (may be incomplete), scan the text below to update the character profiles if new info found. "
                "Return ONLY valid JSON with key 'characters'.\n\n"
                f"Current characters (may be empty): {json.dumps(characters, ensure_ascii=False)}\n\n"
                f"Text:\n{more_text}"
            )
            raw_ref = call_groq(refine_prompt, model="llama-3.1-8b-instant", temperature=0.0)
            parsed_ref = try_parse_json(raw_ref) or try_parse_json(fix_json_with_model(raw_ref))
            if parsed_ref:
                characters = parsed_ref.get("characters", characters)
            st.json(characters)

        # 3) Generate image prompts per scene with strong model
        st.info("Đang sinh prompt ảnh cho từng cảnh (model mạnh)...")
        results = []
        for idx, s in enumerate(scenes, start=1):
            prompt_for_image = (
                "Generate ONE concise English image-generation prompt (single line, no JSON) for the scene below. "
                "Keep characters consistent with this profile and include clear visual details (clothing, setting, mood, camera framing). "
                f"Character profile (Vietnamese): {json.dumps(characters, ensure_ascii=False)}\n\n"
                f"Scene text (Vietnamese):\n{s['text']}\n\n"
                "Output only a single-line English prompt."
            )
            out = call_groq(prompt_for_image, model="llama-3.1-70b-versatile", temperature=0.3)
            if out is None:
                st.error(f"Lỗi khi sinh prompt cho cảnh {idx}. Dừng.")
                st.stop()
            results.append({"id": idx, "text": s['text'], "summary": s['summary'], "prompt": out.strip()})
            time.sleep(PAUSE_BETWEEN_CALLS)

        # 4) Save & download
        story_txt = "\n\n".join([f"[{r['id']}] {r['text']}" for r in results])
        prompt_txt = "\n\n".join([f"[{r['id']}] {r['prompt']}" for r in results])
        json_out = {"segments": results}

        st.download_button("⬇️ Download story_segments.txt", data=story_txt, file_name="story_segments.txt", mime="text/plain")
        st.download_button("⬇️ Download image_prompts.txt", data=prompt_txt, file_name="image_prompts.txt", mime="text/plain")
        st.download_button("⬇️ Download full JSON", data=json.dumps(json_out, ensure_ascii=False, indent=2), file_name="story_prompts.json", mime="application/json")

        st.success("Hoàn tất!")
