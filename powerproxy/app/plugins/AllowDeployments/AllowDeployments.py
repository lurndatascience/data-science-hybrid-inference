"""Declares a plugin which blocks usage of not allowed deployments for clients."""

import json

from fastapi import status
from fastapi.responses import Response
from plugins.base import ImmediateResponseException, PowerProxyPlugin


class AllowDeployments(PowerProxyPlugin):
    """
    Blocks the usage of deployments that are not allowed for the client.

    Allowed deployments are specified in a comma-separated list at the client configuration.
    Access is denied if a client misses the deployments_allowed field.

    Example:
        ...
        clients:
           - name: Team 1
             deployments_allowed: gpt-35-turbo, gpt-4o
        ...
    """

    client_config_jsonschema = {
        "$schema": "http://json-schema.org/draft/2019-09/schema#",
        "$ref": "#/definitions/ClientConfiguration",
        "definitions": {
            "ClientConfiguration": {
                "type": "object",
                "properties": {"deployments_allowed": {"$ref": "#/definitions/DeploymentsAllowed"}},
                "required": ["deployments_allowed"],
            },
            "DeploymentsAllowed": {
                "anyOf": [{"$ref": "#/definitions/DeploymentsArray"}, {"type": "string"}, {"type": "null"}],
            },
            "DeploymentsArray": {"type": "array", "items": {"type": "string"}},
        },
    }

    def on_client_identified(self, routing_slip):
        """Run when the client has been identified."""
        super().on_client_identified(routing_slip)
        client = routing_slip["client"]

        # get the deployment requested
        deployment_requested = routing_slip["virtual_deployment"]

        # get the deployments allowed for the client
        client_settings = self.app_configuration.get_client_settings(client)
        deployments_allowed_list = []
        if isinstance(client_settings["deployments_allowed"], str):
            deployments_allowed_list = [item.strip() for item in client_settings["deployments_allowed"].split(",")]
        if isinstance(client_settings["deployments_allowed"], list):
            deployments_allowed_list = client_settings["deployments_allowed"]

        # raise an exception if the client tries to use a deployment which is not allowed for it
        if deployment_requested not in deployments_allowed_list:
            raise ImmediateResponseException(
                Response(
                    content=json.dumps(
                        {
                            "error": (
                                f"Access to requested deployment '{deployment_requested}' is denied. The PowerProxy "
                                f"configuration for client '{client}' misses a 'deployments_allowed' setting which "
                                "includes that deployment. This needs to be set when the AllowDeployments plugin is "
                                "enabled."
                            )
                        }
                    ),
                    media_type="application/json",
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )
            )
