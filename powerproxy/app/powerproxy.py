"""
PowerProxy for AOAI - reverse proxy to process requests and responses to/from Azure Open AI.

- Use the "Debug powershell.py" launch configuration in VS.Code to develop and debug this script.
- Adjust the launch configuration in VS.Code as needed (esp. for plugins enabled)
"""

import argparse
import asyncio
import io
import json
import random
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from utils import is_time_within_range
import httpx
import uvicorn
from azure.identity import DefaultAzureCredential
from fastapi import FastAPI, Request, status
from fastapi.responses import Response, StreamingResponse
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from helpers.config import Configuration
from helpers.dicts import QueryDict
from helpers.header import print_header
from plugins.base import ImmediateResponseException, foreach_plugin
from version import VERSION

## define script arguments
parser = argparse.ArgumentParser()
# --config-file
parser.add_argument(
    "--config-file",
    type=str,
    help="Path to config file",
    default='../config/config.yaml'  # TODO remove default later
)
# --config-env-var
parser.add_argument(
    "--config-env-var",
    type=str,
    help="Name of the environment variable containing the configuration as JSON string.",
)
# --port
parser.add_argument(
    "--port",
    type=int,
    default=80,
    help=("Port where the proxy runs. Ports <= 1024 may need special permissions in Linux. " "Default: 80."),
)
args, unknown = parser.parse_known_args()

## load configuration
config = Configuration.from_args(args)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan function for FastAPI."""

    # startup
    # print header and config values
    print_header(f"PowerProxy for Azure OpenAI - v{VERSION}")
    Configuration.print_setting("Proxy runs at port", args.port)
    config.print()
    foreach_plugin(config.plugins, "on_print_configuration")

    # collect AOAI targets (endpoints or deployments) and corresponding clients
    app.state.aoai_endpoint_clients = {}
    app.state.aoai_targets = {}
    app.state.virtual_deployment_names = []
    if config.get("aoai/mock_response"):

        async def get_mock_response(request):
            ms_to_wait_before_return = config.get("aoai/mock_response/ms_to_wait_before_return")
            if ms_to_wait_before_return:
                ms_to_wait_before_return = float(ms_to_wait_before_return)
                await asyncio.sleep(ms_to_wait_before_return / 1_000)
            return httpx.Response(200, json=config.get("aoai/mock_response/json"))

        app.state.aoai_endpoint_clients["mock"] = httpx.AsyncClient(
            base_url="https://mock/",
            transport=httpx.MockTransport(get_mock_response),
        )
        app.state.aoai_targets["mock"] = {
            "Mock client": {
                "url": "",
                "key": "",
                "client": app.state.aoai_endpoint_clients["mock"],
                "next_request_not_before_timestamp_ms": 0,
                "non_streaming_fraction": 1,
            }
        }
    else:
        for endpoint in config["aoai/endpoints"]:
            endpoint_qd = QueryDict(endpoint)
            limits = httpx.Limits(
                max_keepalive_connections=int(endpoint_qd["connections/limits/max_keepalive_connections"])
                if endpoint_qd["connections/limits/max_keepalive_connections"]
                else 20,
                max_connections=int(endpoint_qd["connections/limits/max_connections"])
                if endpoint_qd["connections/limits/max_connections"]
                else 100,
                keepalive_expiry=float(endpoint_qd["connections/limits/keepalive_expiry"])
                if endpoint_qd["connections/limits/keepalive_expiry"]
                else 5.0,
            )
            timeout = httpx.Timeout(
                connect=float(endpoint_qd["connections/timeouts/connect"])
                if endpoint_qd["connections/timeouts/connect"]
                else 15.0,
                read=float(endpoint_qd["connections/timeouts/read"])
                if endpoint_qd["connections/timeouts/read"]
                else 120.0,
                write=float(endpoint_qd["connections/timeouts/write"])
                if endpoint_qd["connections/timeouts/write"]
                else 120.0,
                pool=float(endpoint_qd["connections/timeouts/pool"])
                if endpoint_qd["connections/timeouts/pool"]
                else 120.0,
            )
            app.state.aoai_endpoint_clients[endpoint["name"]] = httpx.AsyncClient(
                base_url=endpoint["url"], timeout=timeout, limits=limits
            )
            if "virtual_deployments" in endpoint:
                for virtual_deployment in endpoint["virtual_deployments"]:
                    app.state.virtual_deployment_names.append(virtual_deployment["name"])
                    for standin in virtual_deployment["standins"]:
                        target_name = f"{standin['name']}@{virtual_deployment['name']}@{endpoint['name']}"
                        app.state.aoai_targets[target_name] = {
                            "name": target_name,
                            "type": "virtual_deployment_standin",
                            "endpoint": endpoint["name"],
                            "virtual_deployment": virtual_deployment["name"],
                            "standin": standin["name"],
                            "url": endpoint["url"],
                            "endpoint_client": app.state.aoai_endpoint_clients[endpoint["name"]],
                            "next_request_not_before_timestamp_ms": 0,
                            "non_streaming_fraction": float(
                                standin["non_streaming_fraction"] if "non_streaming_fraction" in standin else 1
                            ),
                        } | ({"endpoint_key": endpoint["key"]} if "key" in endpoint else {})
            else:
                app.state.aoai_targets[endpoint["name"]] = {
                    "name": endpoint["name"],
                    "type": "endpoint",
                    "endpoint": endpoint["name"],
                    "url": endpoint["url"],
                    "endpoint_client": app.state.aoai_endpoint_clients[endpoint["name"]],
                    "next_request_not_before_timestamp_ms": 0,
                    "non_streaming_fraction": float(
                        endpoint["non_streaming_fraction"] if "non_streaming_fraction" in endpoint else 1
                    ),
                } | ({"endpoint_key": endpoint["key"]} if "key" in endpoint else {})

    # get DefaultAzureCredential
    app.state.default_azure_credential = DefaultAzureCredential()

    # print serve notification
    print()
    print("Serving incoming requests...")
    print()

    # run the app
    yield

    # shutdown
    # close AOAI endpoint connections
    for aoai_endpoint_client_name in app.state.aoai_endpoint_clients:
        await app.state.aoai_endpoint_clients[aoai_endpoint_client_name].aclose()


## define and run proxy app
app = FastAPI(lifespan=lifespan)
Instrumentator().instrument(app, metric_namespace='powerproxy', metric_subsystem='aoai').expose(app)
app.add_route("/metrics", metrics)


@app.exception_handler(ImmediateResponseException)
async def exception_callback(request: Request, exception: ImmediateResponseException):
    """Immediately return given response when an ImmediateResponseException is raised."""
    return exception.response


# liveness probe
@app.get(
    "/powerproxy/health/liveness",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Liveness probe for the PowerProxy",
)
async def liveness_probe():
    """
    Return a 204/No Content if the container is live.
    Note: This is required by some hosting services to know if there are issues with the container.
    """
    return None


# all other GETs and POSTs
@app.get("/{path:path}")
@app.post("/{path:path}")
async def handle_request(request: Request, path: str):
    """Handle any incoming request."""
    # create a new routing slip, populate it with some variables and tell plugins about new request
    routing_slip = {
        "request_received_utc": datetime.now(timezone.utc),
        "incoming_request": request,
        "incoming_request_body": await request.body(),
        "path": path,
    }
    routing_slip["virtual_deployment"] = None

    try:
        routing_slip["incoming_request_body_dict"] = await request.json()
    except:
        pass

    deployment_match = re.search(r"(?<=deployments\/)[^\/]+", path)

    if deployment_match:
        routing_slip["virtual_deployment"] = deployment_match.group(0)
    elif routing_slip["incoming_request_body_dict"]["model"] in config.opensource_deployments:
        routing_slip["virtual_deployment"] = routing_slip["incoming_request_body_dict"]["model"]
    routing_slip["incoming_request_body_dict"] = None

    routing_slip["is_non_streaming_response_requested"] = not (
        hasattr(routing_slip["incoming_request_body_dict"], "stream")
        and str(routing_slip["incoming_request_body_dict"]["stream"]).lower() == "true"
    )
    routing_slip["api_version"] = request.query_params["api-version"] if "api-version" in request.query_params else ""
    foreach_plugin(config.plugins, "on_new_request_received", routing_slip)

    # identify client
    # notes: - When API authentication is used, we get an API key in header 'api-key'. This would usually be the API key
    #          for Azure Open AI, but we configure and use client-specific keys here for the proxy to identify the
    #          client. We will replace the API key against the real AOAI key later.
    #        - For Entra ID/Azure AD authentication, we should get no API key but a token in header 'authorization'.
    #          Unfortunately, we cannot interpret or modify that token, so we need another mechanism to identify
    #          clients. In that case, we need a separate instance of PowerProxy for each client, and we use the client
    #          from the config that has 'uses_entra_id_auth: true'.
    #        - Some requests may neither contain an API key nor an Azure AD token. In that case, we need to make sure
    #          that the proxy continues to work.
    headers = {
        key: request.headers[key]
        for key in set(request.headers.keys()) - {"Host", "host", "Content-Length", "content-length"}
    }
    client = None
    if "api-key" in headers:
        if headers["api-key"] not in config.key_client_map:
            raise ImmediateResponseException(
                Response(
                    content=json.dumps(
                        {
                            "error": "The provided API key is not a valid PowerProxy key. Ensure that the 'api-key' "
                            "header contains a valid API key from the PowerProxy's configuration."
                        }
                    ),
                    media_type="application/json",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            )
        client = config.key_client_map[headers["api-key"]] if client is None else client
    elif "authorization" in headers:
        if config.entra_id_client:
            client = config.entra_id_client["name"]
        else:
            raise ImmediateResponseException(
                Response(
                    content=json.dumps(
                        {
                            "error": "When Entra ID/Azure AD is used to authenticate, PowerProxy needs a client in its "
                            "configuration configured with 'uses_entra_id_auth: true', so PowerProxy can map the "
                            "request to a client."
                        }
                    ),
                    media_type="application/json",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            )
    routing_slip["client"] = client
    if client:
        foreach_plugin(config.plugins, "on_client_identified", routing_slip)

    # if virtual deployments are used, make sure the requested deployment is configured
    if (
        app.state.virtual_deployment_names
        and routing_slip["virtual_deployment"] not in app.state.virtual_deployment_names
    ):
        raise ImmediateResponseException(
            Response(
                content=json.dumps(
                    {
                        "error": f"The specified deployment '{routing_slip['virtual_deployment']}' is not available. "
                        "Ensure that you send the request to an existing virtual deployment configured in PowerProxy."
                    }
                ),
                media_type="application/json",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        )

    # get response from AOAI by iterating through the configured targets (endpoints or deployments)
    aoai_response: httpx.Response = None
    for aoai_target_name in app.state.aoai_targets:
        aoai_target = app.state.aoai_targets[aoai_target_name]

        # try next target if this target is blocked
        if aoai_target["next_request_not_before_timestamp_ms"] > get_current_timestamp_in_ms():
            continue

        # try next target if target is virtual_deployment_standin and target's deployment does not match requested
        # deployment
        if (
            aoai_target["type"] == "virtual_deployment_standin"
            and "virtual_deployment" in routing_slip
            and routing_slip["virtual_deployment"] != aoai_target["virtual_deployment"]
        ):
            continue

        # try next target if the non-streaming filter is not passed
        if not passes_non_streaming_filter(
            routing_slip["is_non_streaming_response_requested"], aoai_target["non_streaming_fraction"]
        ):
            continue

        # update auth headers against real API key from AOAI/Entra ID bearer token for AOAI, but only if the request has
        # a (previously successfully verified) API key
        # note: intentionally not raising an exception here if an API key is missing to support requests using
        #       Azure AD/Entra ID authentication. Entra ID requests miss an api-key header but have an Authorization
        #       header, and we pass that as is, so AOAI will do the authentication then for us.
        if "api-key" in headers:
            if "endpoint_key" in aoai_target:
                headers["api-key"] = aoai_target["endpoint_key"] or ""
            else:
                del headers["api-key"]
                if "authorization" in headers:
                    del headers["authorization"]
                if "Authorization" in headers:
                    del headers["Authorization"]
                token = app.state.default_azure_credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                ).token
                headers["Authorization"] = f"Bearer {token}"

        # replace deployment against standin in path if target is deployment standin
        if aoai_target["type"] == "virtual_deployment_standin":
            routing_slip["path"] = re.sub(
                r"/deployments/[^/]+", f"/deployments/{aoai_target['standin']}", routing_slip["path"]
            )

        # remember target and request start time
        routing_slip["aoai_endpoint"] = aoai_target["endpoint"]
        routing_slip["aoai_virtual_deployment"] = (
            aoai_target["virtual_deployment"] if "virtual_deployment" in aoai_target else None
        )
        routing_slip["aoai_standin_deployment"] = aoai_target["standin"] if "standin" in aoai_target else None
        routing_slip["aoai_request_start_time"] = get_current_timestamp_in_ms()

        # send request
        aoai_request = aoai_target["endpoint_client"].build_request(
            request.method,
            routing_slip["path"],
            params=request.query_params,
            headers=headers,
            content=routing_slip["incoming_request_body"],
        )
        aoai_response = await aoai_target["endpoint_client"].send(
            aoai_request,
            stream=(not routing_slip["is_non_streaming_response_requested"]),
        )
        # got http code other than 200 or 401
        if aoai_response.status_code not in [200, 401]:
            # print infos to console
            if not routing_slip["is_non_streaming_response_requested"]:
                await aoai_response.aread()
            print(
                (
                    f"Unexpected HTTP Code {aoai_response.status_code} while using target '{aoai_target['name']}'. "
                    f"Path: {routing_slip['path']} "
                    f"Target Url: {aoai_target['url']}"
                    f"Response: {aoai_response.text}"
                )
            )
        # got 408/Request Timeout, 429/Too Many Requests, or 500/Internal Server Error
        if aoai_response.status_code in [408, 429, 500]:
            # block endpoint for some time, either according to the time given by AOAI or, if not
            # available, for 10 seconds
            waiting_time_ms_until_next_request = (
                int(aoai_response.headers["retry-after-ms"]) if "retry-after-ms" in aoai_response.headers else 10_000
            )
            aoai_target["next_request_not_before_timestamp_ms"] = (
                get_current_timestamp_in_ms() + waiting_time_ms_until_next_request
            )

            # try next target
            continue

        # if we reached here, we found a target which is able to serve our request
        # -> go ahead
        break

    # raise 429 if we could not find any suitable target
    if aoai_response is None:
        raise ImmediateResponseException(
            Response(
                content=json.dumps(
                    {"message": "Could not find any endpoint or deployment with remaining capacity. Try again later."}
                ),
                headers={"retry-after-ms": f"{10_000}"},
                media_type="application/json",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        )

    # process received headers
    routing_slip["headers_from_target"] = aoai_response.headers
    foreach_plugin(config.plugins, "on_headers_from_target_received", routing_slip)

    # determine if it's actually an event stream or not
    routing_slip["is_event_stream"] = (
        "content-type" in aoai_response.headers and "text/event-stream" in aoai_response.headers["content-type"]
    )

    # return different response types depending if it's an event stream or not
    routing_slip["response_headers_from_target"] = {
        header_item[0].decode(): header_item[1].decode() for header_item in aoai_response.headers.raw
    }
    match routing_slip["is_event_stream"]:
        case False:
            # non-streamed response
            body = await aoai_response.aread()
            measure_aoai_roundtrip_time_ms(routing_slip)
            routing_slip['aoai_time_to_response_ms'] = routing_slip['aoai_roundtrip_time_ms']
            try:
                routing_slip["body_dict_from_target"] = json.load(io.BytesIO(body))
                foreach_plugin(config.plugins, "on_body_dict_from_target_available", routing_slip)
            except:
                # eat any exception in case the response cannot be parsed
                pass
            response = Response(
                content=body,
                status_code=aoai_response.status_code,
                headers=routing_slip["response_headers_from_target"],
            )
            if "Transfer-Encoding" in response.headers and "Content-Length" in response.headers:
                del response.headers["Content-Length"]
            return response
        case True:
            # event stream
            # forward and process events as they come in
            # note: see https://learn.microsoft.com/de-de/azure/ai-services/openai/reference
            async def yield_data_events():
                """Stream response while invoking plugins."""
                async for line in aoai_response.aiter_lines():
                    yield f"{line}\r\n"
                    routing_slip["data_from_target"] = None
                    if line.startswith("data: "):
                        if "aoai_time_to_response_ms" not in routing_slip:
                            routing_slip["aoai_time_to_response_ms"] = get_current_timestamp_in_ms() - routing_slip[
                                "aoai_request_start_time"
                            ]
                        data = line[6:]
                        if data != "[DONE]":
                            routing_slip["data_from_target"] = data
                            foreach_plugin(
                                config.plugins,
                                "on_data_event_from_target_received",
                                routing_slip,
                            )
                measure_aoai_roundtrip_time_ms(routing_slip)
                foreach_plugin(
                    config.plugins,
                    "on_end_of_target_response_stream_reached",
                    routing_slip,
                )

            return StreamingResponse(
                yield_data_events(),
                status_code=aoai_response.status_code,
                headers=routing_slip["response_headers_from_target"],
            )


def get_current_timestamp_in_ms():
    """Return the current timestamp in millisecond resolution."""
    return time.time_ns() // 1_000_000


def measure_aoai_roundtrip_time_ms(routing_slip):
    """Measure the roundtrip time from/to Azure OpenAI endpoint."""
    routing_slip["aoai_request_end_time"] = get_current_timestamp_in_ms()
    routing_slip["aoai_roundtrip_time_ms"] = int(
        routing_slip["aoai_request_end_time"] - routing_slip["aoai_request_start_time"]
    )


def passes_non_streaming_filter(is_non_streaming_response_requested, non_streaming_fraction):
    """Determines by chance if a request should be processed or not."""
    return (
        True
        if not is_non_streaming_response_requested
        else not (
            non_streaming_fraction != 1 and (non_streaming_fraction == 0 or random.random() > non_streaming_fraction)
        )
    )


if __name__ == "__main__":
    # note: this applies only when the powerproxy.py script is executed directly. In the Dockerfile provided, we use a
    #       uvicorn command to run the app, so parameters might need to be modified there AS WELL.
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(args.port),
        log_level="warning",
        server_header=False,
        date_header=False,
        proxy_headers=False,
        timeout_keep_alive=120,
        timeout_graceful_shutdown=120,
    )
