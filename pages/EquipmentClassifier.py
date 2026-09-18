import uuid

import requests
import streamlit as st

from services.equipment_classes import CLASS_NAMES
from services.feedback_labels import InvalidLabelError, normalize_label, suggest_close_match
from services.feedback_logic import submit_feedback
from services.feedback_store import FeedbackStoreError
from services.ui import render_chat_widget

st.set_page_config(page_title= "Equipment Classifier Training", page_icon= "📸")

from services.browser_auth import restore_session
restore_session()

st.sidebar.caption("This app is an educational tool, not medical advice.")


API_URL = st.secrets.get("API_URL", "http://127.0.0.1:8080")
SOMETHING_ELSE = "Something else (type it in)"
CLASSIFY_TIMEOUT_SECONDS = 60

st.title("Equipment Classifier Training")
st.write(
    "Upload a photo of gym equipment, see what the model predicts, and tell us "
    "whether it got it right. **You're training the model** — every piece of "
    "feedback you give helps build a better-labeled dataset for the next version."
)
st.caption(
    "Uploaded images and your feedback are stored and used to improve this "
    "model. Please don't upload photos containing people or personal information."
)

if "feedback_session_id" not in st.session_state:
    st.session_state["feedback_session_id"] = str(uuid.uuid4())

upload_file = st.file_uploader("Choose an Image", type= ["jpg","jpeg","png"])

if upload_file is not None:
    st.image(upload_file, caption="Uploaded Image", use_container_width= True)

    upload_signature = (upload_file.name, upload_file.size)
    if st.session_state.get("feedback_upload_signature") != upload_signature:
        st.session_state["feedback_upload_signature"] = upload_signature
        st.session_state["feedback_prediction"] = None
        st.session_state["feedback_stage"] = None

    if st.button("Classify Image"):
        with st.spinner("Classifying... (the model server can take up to a minute to wake up if it's been idle)"):
            files= {"file": (upload_file.name, upload_file.getvalue(), upload_file.type)}
            try:
                response = requests.post(
                    f"{API_URL}/classify-equipment", files=files, timeout=CLASSIFY_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                result= response.json()
                st.session_state["feedback_prediction"] = result
                st.session_state["feedback_raw_bytes"] = upload_file.getvalue()
                st.session_state["feedback_stage"] = "awaiting"
            except requests.exceptions.Timeout:
                st.session_state["feedback_prediction"] = None
                st.error(
                    "The classifier server didn't respond in time. It may be waking up "
                    "from idle — please wait a moment and press **Classify Image** again."
                )
            except requests.exceptions.RequestException as e:
                st.session_state["feedback_prediction"] = None
                st.error(f"Couldnt reach the classifier API: {e}")

    prediction = st.session_state.get("feedback_prediction")
    if prediction:
        st.success(f"**{prediction['equipment']}** - {prediction['confidence']:.1%} confidence")

        top_k = prediction.get("top_k") or []
        if len(top_k) > 1:
            st.write("Top predictions:")
            for entry in top_k:
                st.progress(entry["confidence"], text=f"{entry['equipment']} — {entry['confidence']:.1%}")

        stage = st.session_state.get("feedback_stage")

        st.divider()
        st.write("**Is this correct?**")

        if stage == "submitted":
            st.success("Thanks — this helps improve the model.")
            if st.button("Classify another image"):
                st.session_state["feedback_prediction"] = None
                st.session_state["feedback_stage"] = None
                st.rerun()
        else:
            yes_col, no_col, skip_col = st.columns(3)
            with yes_col:
                yes_clicked = st.button("Yes, correct", use_container_width=True, disabled=stage == "correcting")
            with no_col:
                no_clicked = st.button("No, it's something else", use_container_width=True, disabled=stage == "correcting")
            with skip_col:
                skip_clicked = st.button("Not sure / skip", use_container_width=True, disabled=stage == "correcting")

            def _save_feedback(verdict: str, corrected_label_raw: str | None = None) -> bool:
                try:
                    submit_feedback(
                        raw_bytes=st.session_state["feedback_raw_bytes"],
                        predicted_label=prediction["equipment"],
                        predicted_confidence=prediction["confidence"],
                        top_k_predictions=top_k or None,
                        verdict=verdict,
                        class_names=CLASS_NAMES,
                        session_id=st.session_state["feedback_session_id"],
                        corrected_label_raw=corrected_label_raw,
                    )
                    return True
                except FeedbackStoreError:
                    st.warning("Couldn't reach feedback storage right now, but thanks for classifying!")
                    return True
                except ValueError as error:
                    st.error(str(error))
                    return False

            if yes_clicked:
                if _save_feedback("correct"):
                    st.session_state["feedback_stage"] = "submitted"
                    st.rerun()

            if skip_clicked:
                if _save_feedback("skipped"):
                    st.session_state["feedback_stage"] = "submitted"
                    st.rerun()

            if no_clicked:
                st.session_state["feedback_stage"] = "correcting"
                st.rerun()

            if stage == "correcting":
                st.write("What is it actually?")
                options = list(CLASS_NAMES) + [SOMETHING_ELSE]
                choice = st.selectbox("Known equipment types", options, key="feedback_choice")

                typed_label = ""
                if choice == SOMETHING_ELSE:
                    typed_label = st.text_input("Type the correct equipment name", key="feedback_typed_label")

                    suggestion = None
                    if typed_label.strip():
                        try:
                            suggestion = suggest_close_match(normalize_label(typed_label), CLASS_NAMES)
                        except InvalidLabelError:
                            suggestion = None

                    if suggestion:
                        st.info(f"Did you mean **{suggestion}**?")
                        if st.button(f"Yes, use '{suggestion}'"):
                            if _save_feedback("incorrect", suggestion):
                                st.session_state["feedback_stage"] = "submitted"
                                st.rerun()

                if st.button("Submit correction", use_container_width=True):
                    corrected = typed_label if choice == SOMETHING_ELSE else choice
                    if _save_feedback("incorrect", corrected):
                        st.session_state["feedback_stage"] = "submitted"
                        st.rerun()


from assistant.widget import assistant_widget
assistant_widget()
