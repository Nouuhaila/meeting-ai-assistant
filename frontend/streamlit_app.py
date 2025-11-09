import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Meeting Report Generator",
    layout="wide",
)

st.title("Meeting Report Generator")
st.markdown(
    "Upload a meeting audio file to generate a **full transcript** and a "
    "**structured meeting report** (objectives, topics, decisions, action items)."
)

with st.sidebar:
    st.header("Settings")

    language_hint = st.text_input(
        "Language hint (optional)",
        placeholder="e.g. en, fr",
        help="Leave empty to let the model detect the language.",
    )

    diarization = st.selectbox(
        "Speaker segmentation",
        ["none", "alternate"],
        help="Approximate speaker turns based on pauses in the audio.",
    )

    gap_threshold = st.slider(
        "Pause threshold (seconds)",
        0.2,
        5.0,
        1.0,
        help="If the silence between segments is greater than this, "
             "we switch to the next speaker (for 'alternate' mode).",
    )

    max_speakers = st.slider(
        "Max number of speakers (approx.)",
        1,
        8,
        4,
        help="Used in the heuristic diarization mode.",
    )

    export_pdf = st.checkbox("Export structured report as PDF", value=True)

col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("1. Audio upload")
    audio_file = st.file_uploader(
        "Select an audio file",
        type=["wav", "mp3", "m4a"],
        help="Maximum size depends on your backend configuration.",
    )



lang_to_send = language_hint.strip() if language_hint.strip() else "auto"

tabs = st.tabs(["Transcription", "Meeting Report"])


with tabs[0]:
    st.subheader("Transcription")

    if st.button("Run transcription", type="primary"):
        if not audio_file:
            st.warning("Please upload an audio file first.")
        else:
            params = {
                "diarization": diarization,
                "gap_threshold": gap_threshold,
                "max_speakers": max_speakers,
            }
            if language_hint:
                params["language_hint"] = language_hint

            files = {
                "file": (
                    audio_file.name,
                    audio_file.getvalue(),
                    audio_file.type or "audio/mpeg",
                )
            }

            with st.spinner("Transcribing audio..."):
                try:
                    res = requests.post(
                        f"{API_URL}/reports/transcribe",
                        params=params,
                        files=files,
                        timeout=3600,
                    )
                except requests.Timeout:
                    st.error("Timeout: the backend took too long to respond.")
                except requests.RequestException as e:
                    st.error(f"Network error: {e}")
                else:
                    if not res.ok:
                        try:
                            st.error(res.json().get("detail"))
                        except Exception:
                            st.error(f"HTTP {res.status_code}")
                    else:
                        data = res.json()
                        transcript = data["transcript"]

                        st.success(f"Detected language: {transcript.get('language', 'unknown')}")
                        st.markdown("#### Full text")
                        st.write(transcript.get("text", ""))

                        st.markdown("#### Segments")
                        for i, s in enumerate(transcript.get("segments", [])):
                            speaker = s.get("speaker") or ""
                            st.markdown(
                                f"**{i+1}. {speaker}** "
                                f"[{s.get('start',0):.2f}s → {s.get('end',0):.2f}s]  \n"
                                f"{s.get('text','')}"
                            )


with tabs[1]:
    st.subheader("Meeting report")

    if st.button("Generate report from audio", type="primary"):
        if not audio_file:
            st.warning("Please upload an audio file first.")
        else:
            files = {
                "file": (
                    audio_file.name,
                    audio_file.getvalue(),
                    audio_file.type or "audio/mpeg",
                )
            }
            data = {
                "language_hint": lang_to_send,
                "diarization": diarization,
                "gap_threshold": str(gap_threshold),
                "export_pdf": str(export_pdf).lower(),
            }

            with st.spinner("Generating meeting report..."):
                try:
                    res = requests.post(
                        f"{API_URL}/reports/notes",
                        files=files,
                        data=data,
                        timeout=3600,
                    )
                except requests.Timeout:
                    st.error("Timeout: the backend took too long to respond.")
                except requests.RequestException as e:
                    st.error(f"Network error: {e}")
                else:
                    if not res.ok:
                        try:
                            st.error(res.json().get("detail"))
                        except Exception:
                            st.error(f"HTTP {res.status_code}")
                    else:
                        result = res.json()

                        st.success("Report generated successfully.")

                        st.markdown("#### Language")
                        st.write(result.get("language"))

                        st.markdown("#### Summary")
                        summary = result.get("summary", {})
                        st.write(summary.get("executive_summary"))

                        st.markdown("#### Objectives")
                        objectives = summary.get("objectives", [])
                        if objectives:
                            for i, obj in enumerate(objectives, start=1):
                                st.markdown(f"{i}. {obj}")
                        else:
                            st.write("No objectives extracted.")

                        st.markdown("#### Topics")
                        topics = summary.get("topics", [])
                        if topics:
                            for t in topics:
                                title = t.get("title", "")
                                desc = t.get("description", "")
                                st.markdown(f"**{title}**")
                                if desc:
                                    st.write(desc)
                        else:
                            st.write("No topics extracted.")

                        st.markdown("#### Decisions")
                        decisions = summary.get("decisions", [])
                        if decisions:
                            for d in decisions:
                                st.markdown(f"- {d}")
                        else:
                            st.write("No decisions extracted.")

                        st.markdown("#### Action items")
                        actions = summary.get("actions", [])
                        if actions:
                            for a in actions:
                                owner = a.get("owner") or "-"
                                action_txt = a.get("action") or ""
                                due = a.get("due") or "-"
                                st.markdown(f"- **{owner}**: {action_txt} _(deadline: {due})_")
                        else:
                            st.write("No action items extracted.")

                        st.markdown("#### Outcomes")
                        outcomes = summary.get("outcomes", [])
                        if outcomes:
                            for o in outcomes:
                                st.markdown(f"- {o}")
                        else:
                            st.write("No outcomes extracted.")

                        st.markdown("#### Next steps")
                        next_steps = summary.get("next_steps", [])
                        if next_steps:
                            for ns in next_steps:
                                st.markdown(f"- {ns}")
                        else:
                            st.write("No next steps extracted.")

                        # Fichiers exportés (Markdown / PDF)
                        st.markdown("#### Download exports")
                        exports = result.get("exports", {})

                        md_url_rel = exports.get("markdown_url")
                        pdf_url_rel = exports.get("pdf_url")

                        if md_url_rel:
                            md_url = f"{API_URL}{md_url_rel}"
                            try:
                                md_res = requests.get(md_url, timeout=60)
                                if md_res.ok:
                                    st.download_button(
                                        "Download Markdown",
                                        md_res.content,
                                        file_name="meeting-notes.md",
                                        mime="text/markdown",
                                    )
                                else:
                                    st.warning("Could not fetch Markdown file from backend.")
                            except requests.RequestException as e:
                                st.error(f"Error when downloading Markdown: {e}")

                        if pdf_url_rel:
                            pdf_url = f"{API_URL}{pdf_url_rel}"
                            try:
                                pdf_res = requests.get(pdf_url, timeout=60)
                                if pdf_res.ok:
                                    st.download_button(
                                        "Download PDF",
                                        pdf_res.content,
                                        file_name="meeting-report.pdf",
                                        mime="application/pdf",
                                    )
                                else:
                                    st.warning("Could not fetch PDF file from backend.")
                            except requests.RequestException as e:
                                st.error(f"Error when downloading PDF: {e}")
