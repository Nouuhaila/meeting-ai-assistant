import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("🎙️ Meeting Report Generator — Transcription")
st.write("Upload un fichier audio et récupère la transcription + segments.")

audio_file = st.file_uploader("Choisir un fichier audio", type=["wav", "mp3", "m4a"])
language_hint = st.text_input("Indice de langue (optionnel, ex: fr, en)")
diarization = st.selectbox("Diarisation", ["none", "alternate"])
gap_threshold = st.slider("Seuil de pause (s)", 0.2, 5.0, 1.0)

if st.button("Transcrire !"):
    if not audio_file:
        st.warning("Ajoute d’abord un fichier audio.")
    else:
        params = {
            "diarization": diarization,
            "gap_threshold": gap_threshold,
        }
        if language_hint:
            params["language_hint"] = language_hint

        files = {
            # nom, contenu, type MIME
            "file": (audio_file.name, audio_file, audio_file.type or "audio/mpeg")
        }

        with st.spinner("Transcription en cours…"):
            try:
                res = requests.post(
                    f"{API_URL}/reports/transcribe",
                    params=params,
                    files=files,
                    timeout=3600  # 10 min par sécurité
                )
            except requests.Timeout:
                st.error("⏱️ Timeout : le backend met trop de temps à répondre.")
            except requests.RequestException as e:
                st.error(f"Erreur réseau: {e}")
            else:
                if res.ok:
                    data = res.json()
                    transcript = data["transcript"]
                    st.success(f"Langue détectée : {transcript.get('language', 'inconnue')}")
                    st.subheader("Texte complet")
                    st.write(transcript.get("text", ""))

                    st.subheader("Segments")
                    for i, s in enumerate(transcript.get("segments", [])):
                        speaker = s.get("speaker") or ""
                        st.markdown(
                            f"**{i+1}. {speaker}** "
                            f"[{s.get('start',0):.2f}s → {s.get('end',0):.2f}s] : {s.get('text','')}"
                        )
                else:
                    try:
                        st.error(res.json().get("detail"))
                    except Exception:
                        st.error(f"HTTP {res.status_code}")
