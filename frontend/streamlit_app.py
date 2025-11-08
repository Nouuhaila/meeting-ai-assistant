import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("🎙️ Meeting Report Generator")

st.write("Upload un fichier audio pour :")
st.markdown("- Obtenir la **transcription complète**")
st.markdown("- Générer des **notes de réunion structurées** (sujets, décisions, actions)")

audio_file = st.file_uploader("Choisir un fichier audio", type=["wav", "mp3", "m4a"])

language_hint = st.text_input(
    "Indice de langue (optionnel, ex: fr, en — laisser vide pour détection automatique)"
)

diarization = st.selectbox("Diarisation", ["none", "alternate"])
gap_threshold = st.slider("Seuil de pause (s)", 0.2, 5.0, 1.0)

lang_to_send = language_hint.strip()


st.header("1️⃣ Transcription brute")

if st.button("Transcrire !"):
    if not audio_file:
        st.warning("Ajoute d’abord un fichier audio.")
    else:
        params = {
            "diarization": diarization,
            "gap_threshold": gap_threshold,
        }
        if lang_to_send:
            params["language_hint"] = lang_to_send

        files = {
            "file": (
                audio_file.name,
                audio_file.getvalue(),        # on envoie les bytes
                audio_file.type or "audio/mpeg",
            )
        }

        with st.spinner("Transcription en cours…"):
            try:
                res = requests.post(
                    f"{API_URL}/reports/transcribe",
                    params=params,
                    files=files,
                    timeout=3600,
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


#  GÉNÉRATION DE NOTES + EXPORTS

st.header("2️⃣ Génération de notes de réunion")

export_pdf = st.checkbox("Exporter aussi en PDF", value=False)

if st.button("Générer les notes à partir de l'audio"):
    if not audio_file:
        st.warning("Ajoute d’abord un fichier audio.")
    else:
        files = {
            "file": (
                audio_file.name,
                audio_file.getvalue(),
                audio_file.type or "audio/mpeg",
            )
        }
        # /reports/notes attend des champs de FORM
        data = {
            "language_hint": lang_to_send,
            "diarization": diarization,
            "gap_threshold": str(gap_threshold),
            "export_pdf": str(export_pdf).lower(),    # "true" / "false"
        }

        with st.spinner("Génération des notes en cours…"):
            try:
                res = requests.post(
                    f"{API_URL}/reports/notes",
                    files=files,
                    data=data,
                    timeout=3600,
                )
            except requests.Timeout:
                st.error("⏱️ Timeout : le backend met trop de temps à répondre.")
            except requests.RequestException as e:
                st.error(f"Erreur réseau: {e}")
            else:
                if not res.ok:
                    try:
                        st.error(res.json().get("detail"))
                    except Exception:
                        st.error(f"HTTP {res.status_code}")
                else:
                    result = res.json()

                    st.success("✅ Notes générées avec succès")

                    st.subheader("Langue détectée")
                    st.write(result.get("language"))

                    st.subheader("Transcript (aperçu)")
                    txt = result.get("transcript_text", "")
                    st.write(txt[:2000] + ("..." if len(txt) > 2000 else ""))

                    summary = result.get("summary", {})

                    st.subheader("🧩 Sujets abordés")
                    topics = summary.get("topics", [])
                    if topics:
                        for t in topics:
                            title = t.get("title", "")
                            desc = t.get("description", "")
                            st.markdown(f"- **{title}** — {desc}")
                    else:
                        st.write("Aucun sujet détecté.")

                    st.subheader("✅ Décisions")
                    decisions = summary.get("decisions", [])
                    if decisions:
                        for d in decisions:
                            # d est un dict venant du JSON de l'API
                            if isinstance(d, dict):
                                txt = d.get("decision", "")
                                due = d.get("due")
                                if due:
                                    st.markdown(f"- **{txt}** _(échéance : {due})_")
                                else:
                                    st.markdown(f"- {txt}")
                            else:
                                st.markdown(f"- {d}")
                    else:
                        st.write("Aucune décision extraite.")


                    st.subheader("📝 Actions à réaliser")
                    actions = summary.get("actions", [])
                    if actions:
                        for a in actions:
                            st.markdown(f"- {a}")
                    else:
                        st.write("Aucune action extraite.")

                    st.subheader("📂 Fichiers exportés")
                    exports = result.get("exports", {})

                    md_url_rel = exports.get("markdown_url")
                    pdf_url_rel = exports.get("pdf_url")

                    if not md_url_rel and not pdf_url_rel:
                        st.write("Aucun fichier exporté (markdown_url / pdf_url non fournis par l'API).")
                        st.json(exports)  
                    else:
                        if md_url_rel:
                            md_url = f"{API_URL}{md_url_rel}"
                            try:
                                md_res = requests.get(md_url, timeout=60)
                                if md_res.ok:
                                    st.download_button(
                                        "⬇️ Télécharger le Markdown",
                                        md_res.content,
                                        file_name="meeting-notes.md",
                                        mime="text/markdown",
                                    )
                                else:
                                    st.warning("Impossible de récupérer le fichier Markdown.")
                            except requests.RequestException as e:
                                st.error(f"Erreur lors du téléchargement du Markdown : {e}")

                        #Téléchargement du PDF
                        if pdf_url_rel:
                            pdf_url = f"{API_URL}{pdf_url_rel}"
                            try:
                                pdf_res = requests.get(pdf_url, timeout=60)
                                if pdf_res.ok:
                                    st.download_button(
                                        "⬇️ Télécharger le PDF",
                                        pdf_res.content,
                                        file_name="meeting-notes.pdf",
                                        mime="application/pdf",
                                    )
                                else:
                                    st.warning("Impossible de récupérer le fichier PDF.")
                            except requests.RequestException as e:
                                st.error(f"Erreur lors du téléchargement du PDF : {e}")
