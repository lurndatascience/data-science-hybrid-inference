"""Declares the custom base class for a plugin that logs usage information."""

from abc import abstractmethod
import re
from plugins.base import TokenCountingPlugin


class LogUsageCustomBase(TokenCountingPlugin):
    """Base class for a plugin that logs usage."""

    aoai_region = None
    deployment_id_pattern = r'.*/deployments/([a-zA-Z0-9_-]+)/.*'

    def on_new_request_received(self, routing_slip):
        """Run when a new request is received."""
        super().on_new_request_received(routing_slip)

        self.aoai_region = None

    def on_headers_from_target_received(self, routing_slip):
        """Run when headers from target have been received."""
        super().on_headers_from_target_received(routing_slip)

        headers_from_target = routing_slip["headers_from_target"]
        for header, value in headers_from_target.items():
            if header == "x-ms-region":
                self.aoai_region = value

    def on_body_dict_from_target_available(self, routing_slip):
        """Run when the body was received from AOAI (only for one-time, non-streaming requests)."""
        super().on_body_dict_from_target_available(routing_slip)

        # extract deployment ID
        re_match = re.match(self.deployment_id_pattern, routing_slip["path"])
        deployment_id = re_match.group(1) if re_match else None

        self._append_line(
            request_received_utc=routing_slip["request_received_utc"],
            client=routing_slip["client"],
            is_streaming=False,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            aoai_roundtrip_time_ms=routing_slip["aoai_roundtrip_time_ms"],
            aoai_region=self.aoai_region,
            aoai_endpoint=routing_slip["aoai_endpoint"],
            aoai_deployment_id=deployment_id,
            aoai_time_to_response_ms=routing_slip["aoai_time_to_response_ms"]
        )

    def on_end_of_target_response_stream_reached(self, routing_slip):
        """Process the end of a stream (needs streaming requested)."""
        super().on_end_of_target_response_stream_reached(routing_slip)

        # extract deployment ID
        re_match = re.match(self.deployment_id_pattern, routing_slip["path"])
        deployment_id = re_match.group(1) if re_match else None

        self._append_line(
            request_received_utc=routing_slip["request_received_utc"],
            client=routing_slip["client"],
            is_streaming=True,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            aoai_roundtrip_time_ms=routing_slip["aoai_roundtrip_time_ms"],
            aoai_region=self.aoai_region,
            aoai_endpoint=routing_slip["aoai_endpoint"],
            aoai_deployment_id=deployment_id,
            aoai_time_to_response_ms=routing_slip["aoai_time_to_response_ms"],

        )

    @abstractmethod
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
        aoai_time_to_response_ms,
    ):
        pass
