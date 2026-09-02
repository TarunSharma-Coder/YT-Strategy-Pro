from typing import Iterable, Mapping

import streamlit as st


def render_metric_cards(metrics: Iterable[Mapping[str, object]]) -> None:
    with st.container(horizontal=True):
        for metric in metrics:
            st.metric(
                str(metric.get("label", "")),
                str(metric.get("value", "")),
                delta=metric.get("delta"),
                border=True,
            )
