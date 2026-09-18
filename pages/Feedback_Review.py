import csv
import io

import streamlit as st

from services.feedback_store import (
    FeedbackStoreError,
    delete_record,
    get_confusion_table,
    get_exportable_records,
    get_new_class_labels,
    get_recent_records,
    get_summary_counts,
    update_record,
)
from services.feedback_storage import get_storage_backend
from services.ui import render_chat_widget

st.set_page_config(page_title="Feedback Review", page_icon="🔍", layout="wide")

from services.browser_auth import restore_session
restore_session()

st.sidebar.caption("This app is an educational tool, not medical advice.")

st.title("Classifier Feedback Review")
st.page_link("BMI2.py", label="← Back to Home")

ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")

if not ADMIN_PASSWORD:
    st.error("Add ADMIN_PASSWORD to Streamlit secrets to enable this page.")
    render_chat_widget()
    st.stop()

if not st.session_state.get("feedback_review_authenticated"):
    entered_password = st.text_input("Admin password", type="password")
    if st.button("Log in"):
        if entered_password == ADMIN_PASSWORD:
            st.session_state["feedback_review_authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    render_chat_widget()
    st.stop()

try:
    counts = get_summary_counts()
    confusion_rows = get_confusion_table()
    new_class_rows = get_new_class_labels()
    recent_records = get_recent_records(limit=25)
except FeedbackStoreError as error:
    st.error(f"Could not load feedback data: {error}")
    render_chat_widget()
    st.stop()

correct = counts["correct"]
incorrect = counts["incorrect"]
skipped = counts["skipped"]
total = correct + incorrect + skipped

metric_columns = st.columns(4)
metric_columns[0].metric("Total records", total)
metric_columns[1].metric("Correct", correct)
metric_columns[2].metric("Incorrect", incorrect)
metric_columns[3].metric("Skipped", skipped)

accuracy_denominator = correct + incorrect
accuracy = (correct / accuracy_denominator) if accuracy_denominator else None
st.metric(
    "Model accuracy from user feedback",
    f"{accuracy:.1%}" if accuracy is not None else "N/A",
    help="correct / (correct + incorrect); skipped records are excluded.",
)

st.caption(f"Image storage backend: {get_storage_backend()}")

st.divider()

st.subheader("Confusion table")
st.caption("Predicted label vs. final (corrected) label, most frequent mistakes first.")
if confusion_rows:
    st.dataframe(
        [
            {
                "Predicted": row["predicted_label"],
                "Actually": row["final_label"],
                "Count": row["count"],
            }
            for row in confusion_rows
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No corrections recorded yet.")

st.divider()

st.subheader("Candidate new classes")
st.caption("Corrected labels that aren't in the model's current class list.")
if new_class_rows:
    st.dataframe(
        [{"Label": row["final_label"], "Count": row["count"]} for row in new_class_rows],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No new-class candidates yet.")

st.divider()

st.subheader("Export training data")
try:
    exportable = get_exportable_records()
except FeedbackStoreError as error:
    exportable = []
    st.error(f"Could not load exportable records: {error}")

st.caption(f"{len(exportable)} labeled record(s) ready to export (final_label set, not yet used in training).")
if exportable:
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["image_key", "final_label"])
    for row in exportable:
        writer.writerow([row["image_key"], row["final_label"]])
    st.download_button(
        "Download CSV",
        data=csv_buffer.getvalue(),
        file_name="classifier_training_export.csv",
        mime="text/csv",
    )

st.divider()

st.subheader("Recent records")
if not recent_records:
    st.info("No feedback recorded yet.")
else:
    for record in recent_records:
        title = (
            f"#{record['id']} · {record['predicted_label']} "
            f"({record['predicted_confidence']:.1%}) · {record['user_verdict']}"
        )
        with st.expander(title):
            if record["image_key"]:
                st.code(record["image_key"], language=None)
            detail_columns = st.columns(2)
            detail_columns[0].write(f"**Final label:** {record['final_label'] or '—'}")
            detail_columns[1].write(f"**New class:** {'Yes' if record['is_new_class'] else 'No'}")
            st.caption(f"Created at {record['created_at']}")

            with st.form(f"edit_record_{record['id']}"):
                new_label = st.text_input(
                    "Edit final label",
                    value=record["final_label"] or "",
                    key=f"label_{record['id']}",
                )
                save_clicked = st.form_submit_button("Save label")

            if save_clicked:
                try:
                    update_record(record["id"], new_label.strip() or None)
                    st.success("Updated.")
                    st.rerun()
                except FeedbackStoreError as error:
                    st.error(f"Could not update record: {error}")

            confirm_key = f"confirm_delete_{record['id']}"
            st.checkbox("I understand this permanently deletes the record.", key=confirm_key)
            if st.button(
                "Delete record",
                key=f"delete_{record['id']}",
                disabled=not st.session_state.get(confirm_key, False),
            ):
                try:
                    delete_record(record["id"])
                    st.success("Deleted.")
                    st.rerun()
                except FeedbackStoreError as error:
                    st.error(f"Could not delete record: {error}")

render_chat_widget()
