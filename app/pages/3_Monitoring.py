from __future__ import annotations

import altair as alt
import streamlit as st

from app.core import metrics
from app.core.settings import get_settings

st.set_page_config(page_title="Monitoring", page_icon="📈", layout="wide")

try:
    settings = get_settings()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

metrics.init_metrics_db(settings.metrics_db)
summary = metrics.fetch_summary(settings.metrics_db)

col1, col2, col3 = st.columns(3)
col1.metric("Requêtes totales", summary.get("total_requests", 0))
col2.metric(
    "Taux succès",
    f"{summary['success_rate'] * 100:.1f}%" if summary.get("total_requests") else "0%",
)
col3.metric(
    "Latence totale moyenne",
    f"{summary['avg_total_ms']:.0f} ms" if summary.get("avg_total_ms") else "N/A",
)

if not summary.get("total_requests"):
    st.info(
        "Pas encore de données. Posez une question dans le chat pour alimenter le monitoring."
    )
    st.stop()

st.subheader("Requêtes dans le temps")
requests_ts = metrics.fetch_request_timeseries(settings.metrics_db)
if requests_ts:
    req_chart = (
        alt.Chart(alt.Data(values=requests_ts))
        .transform_fold(["total", "success"], as_=["metric", "value"])
        .mark_line(point=True)
        .encode(
            x=alt.X(
                "bucket:T",
                title="",
                axis=alt.Axis(labelAngle=-35, labelColor="#444", titleColor="#444"),
            ),
            y=alt.Y("value:Q", title="Volume"),
            color=alt.Color(
                "metric:N",
                title="",
                legend=alt.Legend(orient="bottom", direction="horizontal"),
            ),
            tooltip=["bucket:T", "metric:N", "value:Q"],
        )
    )
    st.altair_chart(req_chart, use_container_width=True)
else:
    st.info("Aucune requête tracée pour le moment.")

st.subheader("Latence moyenne")
latency_ts = metrics.fetch_latency_timeseries(settings.metrics_db)
if latency_ts:
    latency_chart = (
        alt.Chart(alt.Data(values=latency_ts))
        .mark_line(point=True, color="steelblue")
        .encode(
            x=alt.X(
                "bucket:T",
                title="",
                axis=alt.Axis(labelAngle=-35, labelColor="#444", titleColor="#444"),
            ),
            y=alt.Y("avg_total_ms:Q", title=""),
            tooltip=["bucket:T", "avg_total_ms:Q"],
        )
    )
    st.altair_chart(latency_chart, use_container_width=True)
else:
    st.info("Aucune latence mesurée pour le moment.")

# st.subheader("Prompts avant la première bonne réponse")
# prompts_data, avg_prompts = metrics.fetch_prompts_to_success(settings.metrics_db)
# if prompts_data:
#     prompts_chart = (
#         alt.Chart(alt.Data(values=prompts_data))
#         .mark_bar()
#         .encode(
#             x=alt.X("created_at:T", title="Horodatage"),
#             y=alt.Y("prompt_index:Q", title="Nombre de prompts"),
#             tooltip=["conv_id:N", "prompt_index:Q", "created_at:T"],
#         )
#     )
#     st.altair_chart(prompts_chart, use_container_width=True)
#     if avg_prompts is not None:
#         st.caption(f"Moyenne: {avg_prompts:.2f} prompts avant une réponse satisfaisante.")
# else:
#     st.info("Aucune conversation avec réponse satisfaisante pour le moment.")
