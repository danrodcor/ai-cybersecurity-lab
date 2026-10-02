"""Local graphical interface for human approval decisions."""

import os
import sys
from pathlib import Path
from typing import Any

import boto3
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.reviewer_interface.service import (
    list_pending_approvals,
)
from src.reviewer_interface.service import (
    load_approval_request,
)
from src.reviewer_interface.service import submit_decision


def required_environment_variable(name: str) -> str:
    """Return one required environment variable."""
    value = os.environ.get(name, "").strip()

    if not value:
        raise RuntimeError(
            f"Required environment variable is missing: {name}"
        )

    return value


@st.cache_resource
def create_clients(
    region: str,
) -> tuple[Any, Any, Any]:
    """Create reusable AWS clients."""
    return (
        boto3.client("dynamodb", region_name=region),
        boto3.client("s3", region_name=region),
        boto3.client("lambda", region_name=region),
    )


def main() -> None:
    """Render the local reviewer interface."""
    st.set_page_config(
        page_title="CloudSec Approval Review",
        page_icon="🛡️",
        layout="wide",
    )

    st.title("CloudSec Approval Review")
    st.caption(
        "Human approval interface — response mode is "
        "restricted to DRY_RUN."
    )

    region = os.environ.get(
        "AWS_REGION",
        "us-east-1",
    )

    try:
        table_name = required_environment_variable(
            "INCIDENT_TABLE_NAME"
        )
        bucket_name = required_environment_variable(
            "EVIDENCE_BUCKET_NAME"
        )
        function_name = required_environment_variable(
            "APPROVAL_DECISION_FUNCTION_NAME"
        )
    except RuntimeError as error:
        st.error(str(error))
        st.stop()

    dynamodb_client, s3_client, lambda_client = (
        create_clients(region)
    )

    try:
        approvals = list_pending_approvals(
            dynamodb_client,
            table_name,
        )
    except Exception as error:
        st.error(
            f"Unable to read pending approvals: {error}"
        )
        st.stop()

    if not approvals:
        st.info("There are no pending approval requests.")
        st.stop()

    selected = st.selectbox(
        "Pending approval",
        approvals,
        format_func=lambda item: (
            f"{item['finding_id']} | "
            f"expires {item['expires_at']}"
        ),
    )

    try:
        request = load_approval_request(
            s3_client,
            bucket_name,
            selected["request_key"],
        )
    except Exception as error:
        st.error(
            f"Unable to load approval evidence: {error}"
        )
        st.stop()

    summary_column, metadata_column = st.columns(
        [2, 1]
    )

    with summary_column:
        st.subheader("Investigation summary")
        st.write(request["summary"])

        st.subheader("Proposed actions")

        for action in request["proposed_actions"]:
            st.markdown(f"- {action}")

    with metadata_column:
        st.metric(
            "Confidence",
            request["confidence"],
        )
        st.metric(
            "Provider",
            request["provider"],
        )
        st.metric(
            "Response mode",
            request["response_mode"],
        )
        st.write(f"**Model:** `{request['model_id']}`")
        st.write(
            f"**Expires:** `{request['expires_at']}`"
        )

    with st.expander("Approval evidence"):
        st.json(request)

    st.warning(
        "Approval authorizes only a simulated response. "
        "No containment action will be executed."
    )

    reviewer = st.text_input(
        "Reviewer identity",
        value=os.environ.get(
            "APPROVAL_REVIEWER_ID",
            "",
        ),
    )

    comment = st.text_area(
        "Decision comment",
        help=(
            "Required for rejection and recommended "
            "for approval."
        ),
    )

    approve_column, reject_column = st.columns(2)

    with approve_column:
        approve = st.button(
            "Approve dry run",
            type="primary",
            use_container_width=True,
            disabled=not reviewer.strip(),
        )

    with reject_column:
        reject = st.button(
            "Reject",
            use_container_width=True,
            disabled=(
                not reviewer.strip()
                or not comment.strip()
            ),
        )

    selected_decision = None

    if approve:
        selected_decision = "APPROVED"
    elif reject:
        selected_decision = "REJECTED"

    if selected_decision is not None:
        try:
            result = submit_decision(
                lambda_client=lambda_client,
                function_name=function_name,
                approval_request=request,
                decision=selected_decision,
                decided_by=reviewer,
                comment=comment,
            )
        except Exception as error:
            st.error(f"Decision failed: {error}")
        else:
            st.success(
                f"Decision recorded: {selected_decision}"
            )
            st.json(result["approval_decision"])


if __name__ == "__main__":
    main()