"""Declares a plugin to log custom usage infos to console."""

from plugins.LogUsageCustom.LogUsageCustomBase import LogUsageCustomBase


class LogUsageCustomToConsole(LogUsageCustomBase):
    """Logs Azure OpenAI custom usage infos to console."""

    def _append_line(
        self,
        request_received_utc,
        client,
        is_streaming,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        aoai_roundtrip_time_ms,
        aoai_region,
        aoai_endpoint,
        aoai_deployment_id,
        aoai_time_to_response_ms
    ):
        """Append a new line with the given infos."""
        print(
            {
                "request_received_utc": str(request_received_utc),
                "client": client,
                "is_streaming": is_streaming,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "aoai_roundtrip_time_ms": aoai_roundtrip_time_ms,
                "aoai_region": aoai_region,
                "aoai_endpoint": aoai_endpoint,
                "aoai_deployment_id": aoai_deployment_id,
                "aoai_time_to_response_ms": aoai_time_to_response_ms,
            }
        )
