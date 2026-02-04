from google.cloud import bigquery
from google.api_core import exceptions
from datetime import datetime, timedelta, timezone

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
PROJECT_ID = "clariversev1"

SOURCE_TABLE = "clariversev1.flipkart_slices.sec_voice_metrics_hourly"
TARGET_TABLE = "clariversev1.flipkart_slices.sec_voice_metrics_weekly"

WINDOW_DURATION = timedelta(days=7)
client = bigquery.Client(project=PROJECT_ID)

# --------------------------------------------------
# UTILS
# --------------------------------------------------
def create_table_if_not_exists():
    try:
        client.get_table(TARGET_TABLE)
        return
    except exceptions.NotFound:
        pass

    schema = [
        bigquery.SchemaField("job_id", "STRING", "REQUIRED"),
        bigquery.SchemaField("job_name", "STRING", "REQUIRED"),
        bigquery.SchemaField("job_start_ts", "TIMESTAMP", "REQUIRED"),
        bigquery.SchemaField("job_end_ts", "TIMESTAMP", "REQUIRED"),
        bigquery.SchemaField("window_type", "STRING", "REQUIRED"),
        bigquery.SchemaField("window_start_ts", "TIMESTAMP", "REQUIRED"),
        bigquery.SchemaField("window_end_ts", "TIMESTAMP", "REQUIRED"),
        bigquery.SchemaField("window_date", "DATE", "REQUIRED"),

        bigquery.SchemaField("source_event_count", "INTEGER"),
        bigquery.SchemaField("processing_latency_sec", "FLOAT"),
        bigquery.SchemaField("total_volume", "INTEGER"),

        bigquery.SchemaField("empathy_qa_score", "FLOAT"),
        bigquery.SchemaField("tone_qa_score", "FLOAT"),
        bigquery.SchemaField("resolution_qa_score", "FLOAT"),
        bigquery.SchemaField("listening_qa_score", "FLOAT"),
        bigquery.SchemaField("team_qa_score", "FLOAT"),

        bigquery.SchemaField("escalation_risk_pct", "FLOAT"),
        bigquery.SchemaField("escalation_risk_trend", "FLOAT"),
        bigquery.SchemaField("escalation_hot_hour_index", "FLOAT"),

        bigquery.SchemaField("escalation_requested_count", "INTEGER"),
        bigquery.SchemaField("high_risk_calls", "INTEGER"),
        bigquery.SchemaField("escalation_agent_true_count", "INTEGER"),

        bigquery.SchemaField("dominant_cluster_frequency", "STRING"),
        bigquery.SchemaField("top_volume_dominant_cluster", "STRING"),

        bigquery.SchemaField("violation_count", "INTEGER"),
        bigquery.SchemaField("active_violations", "INTEGER"),
        bigquery.SchemaField("compliance_score", "FLOAT"),

        bigquery.SchemaField("negative_sentiment_rate", "FLOAT"),
        bigquery.SchemaField("urgent_volume", "INTEGER"),
        bigquery.SchemaField("sla_breach_risk_pct", "FLOAT"),

        bigquery.SchemaField("eisenhower_do_now_pct", "FLOAT"),
        bigquery.SchemaField("eisenhower_schedule_pct", "FLOAT"),
        bigquery.SchemaField("eisenhower_delegate_pct", "FLOAT"),
        bigquery.SchemaField("eisenhower_postpone_pct", "FLOAT"),

        bigquery.SchemaField("pending_from_company_pct", "FLOAT"),
        bigquery.SchemaField("repeat_complaint_rate", "FLOAT"),

        bigquery.SchemaField("escalation_driver_agent_tone_issues_pct", "FLOAT"),

        bigquery.SchemaField("average_handle_time_sec", "FLOAT"),
        bigquery.SchemaField("inserted_at", "TIMESTAMP", "REQUIRED"),
    ]

    client.create_table(bigquery.Table(TARGET_TABLE, schema=schema))


def get_last_processed_week_end():
    query = f"""
        SELECT MAX(window_end_ts)
        FROM `{TARGET_TABLE}`
        WHERE window_type = 'WEEK'
    """
    result = list(client.query(query).result())[0][0]

    if result:
        return result

    query = f"""
        SELECT MIN(window_start_ts)
        FROM `{SOURCE_TABLE}`
        WHERE window_type = 'HOUR'
    """
    return list(client.query(query).result())[0][0]


def align_to_week(ts: datetime) -> datetime:
    # Monday 00:00 UTC
    start = ts - timedelta(days=ts.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

# --------------------------------------------------
# MAIN LOGIC
# --------------------------------------------------
def run_weekly_aggregation():
    job_start_ts = datetime.now(timezone.utc)

    create_table_if_not_exists()

    last_processed_end = get_last_processed_week_end()
    if last_processed_end is None:
        print("❌ No hourly source data available.")
        return

    current_week_start = align_to_week(last_processed_end)

    # ✅ FIX: do NOT align now_ts
    now_ts = datetime.now(timezone.utc)

    if current_week_start >= now_ts:
        print("✅ No new weekly windows to process.")
        return

    insert_query = f"""
    INSERT INTO `{TARGET_TABLE}`
    WITH weekly_base AS (
        SELECT
            DATE(TIMESTAMP_TRUNC(window_start_ts, WEEK(MONDAY))) AS week_date,
            TIMESTAMP_TRUNC(window_start_ts, WEEK(MONDAY)) AS week_start,
            TIMESTAMP_ADD(
                TIMESTAMP_TRUNC(window_start_ts, WEEK(MONDAY)),
                INTERVAL 7 DAY
            ) AS week_end,
            *
        FROM `{SOURCE_TABLE}`
        WHERE window_type = 'HOUR'
    ),

    aggregated AS (
        SELECT
            week_start,
            week_end,
            week_date,

            SUM(source_event_count) AS source_event_count,
            SUM(total_volume) AS total_volume,

            SAFE_DIVIDE(SUM(empathy_qa_score * total_volume), SUM(total_volume)) AS empathy_qa_score,
            SAFE_DIVIDE(SUM(tone_qa_score * total_volume), SUM(total_volume)) AS tone_qa_score,
            SAFE_DIVIDE(SUM(resolution_qa_score * total_volume), SUM(total_volume)) AS resolution_qa_score,
            SAFE_DIVIDE(SUM(listening_qa_score * total_volume), SUM(total_volume)) AS listening_qa_score,
            SAFE_DIVIDE(SUM(team_qa_score * total_volume), SUM(total_volume)) AS team_qa_score,

            SAFE_DIVIDE(SUM(escalation_risk_pct * total_volume), SUM(total_volume)) AS escalation_risk_pct,

            SUM(escalation_requested_count) AS escalation_requested_count,
            SUM(high_risk_calls) AS high_risk_calls,
            SUM(escalation_agent_true_count) AS escalation_agent_true_count,

            SUM(violation_count) AS violation_count,
            SUM(active_violations) AS active_violations,

            SAFE_DIVIDE(SUM(compliance_score * total_volume), SUM(total_volume)) AS compliance_score,
            SAFE_DIVIDE(SUM(negative_sentiment_rate * total_volume), SUM(total_volume)) AS negative_sentiment_rate,
            SUM(urgent_volume) AS urgent_volume,
            SAFE_DIVIDE(SUM(sla_breach_risk_pct * total_volume), SUM(total_volume)) AS sla_breach_risk_pct,

            SAFE_DIVIDE(SUM(eisenhower_do_now_pct * total_volume), SUM(total_volume)) AS eisenhower_do_now_pct,
            SAFE_DIVIDE(SUM(eisenhower_schedule_pct * total_volume), SUM(total_volume)) AS eisenhower_schedule_pct,
            SAFE_DIVIDE(SUM(eisenhower_delegate_pct * total_volume), SUM(total_volume)) AS eisenhower_delegate_pct,
            SAFE_DIVIDE(SUM(eisenhower_postpone_pct * total_volume), SUM(total_volume)) AS eisenhower_postpone_pct,

            SAFE_DIVIDE(SUM(pending_from_company_pct * total_volume), SUM(total_volume)) AS pending_from_company_pct,
            SAFE_DIVIDE(SUM(repeat_complaint_rate * total_volume), SUM(total_volume)) AS repeat_complaint_rate,

            SAFE_DIVIDE(
                SUM(escalation_agent_true_count),
                SUM(escalation_requested_count)
            ) AS escalation_driver_agent_tone_issues_pct,

            SAFE_DIVIDE(SUM(average_handle_time_sec * total_volume), SUM(total_volume)) AS average_handle_time_sec,

            ANY_VALUE(dominant_cluster_frequency) AS dominant_cluster_frequency,
            ANY_VALUE(top_volume_dominant_cluster) AS top_volume_dominant_cluster,

            MAX(escalation_requested_count) AS max_hourly_escalations,
            AVG(escalation_requested_count) AS avg_hourly_escalations

        FROM weekly_base
        GROUP BY week_start, week_end, week_date
    ),

    with_trend AS (
        SELECT
            *,
            escalation_risk_pct
              - LAG(escalation_risk_pct) OVER (ORDER BY week_start)
              AS escalation_risk_trend,

            SAFE_DIVIDE(max_hourly_escalations, avg_hourly_escalations)
              AS escalation_hot_hour_index
        FROM aggregated
    )

    SELECT
        GENERATE_UUID(),
        'sec_voice_metrics_weekly',
        TIMESTAMP('{job_start_ts}'),
        CURRENT_TIMESTAMP(),
        'WEEK',

        week_start,
        week_end,
        week_date,

        source_event_count,
        TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), TIMESTAMP('{job_start_ts}'), SECOND),
        total_volume,

        empathy_qa_score,
        tone_qa_score,
        resolution_qa_score,
        listening_qa_score,
        team_qa_score,

        escalation_risk_pct,
        escalation_risk_trend,
        escalation_hot_hour_index,

        escalation_requested_count,
        high_risk_calls,
        escalation_agent_true_count,

        dominant_cluster_frequency,
        top_volume_dominant_cluster,

        violation_count,
        active_violations,
        compliance_score,

        negative_sentiment_rate,
        urgent_volume,
        sla_breach_risk_pct,

        eisenhower_do_now_pct,
        eisenhower_schedule_pct,
        eisenhower_delegate_pct,
        eisenhower_postpone_pct,

        pending_from_company_pct,
        repeat_complaint_rate,
        escalation_driver_agent_tone_issues_pct,

        average_handle_time_sec,
        CURRENT_TIMESTAMP()
    FROM with_trend
    """

    client.query(insert_query).result()
    print("🎉 Weekly aggregation completed successfully")

# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    run_weekly_aggregation()