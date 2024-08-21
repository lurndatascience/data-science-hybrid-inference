"""Declares a plugin to log usage infos to a CSV file."""

from azure.identity import ClientSecretCredential, DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.ingestion import LogsIngestionClient
from helpers.config import Configuration
from helpers.dicts import QueryDict
from plugins.LogUsage.LogUsageBase import LogUsageBase


class LogUsageToLogAnalytics(LogUsageBase):
    """Logs Azure OpenAI usage info to a Log Analytics table."""

    log_ingestion_endpoint = None
    credential_tenant_id = None
    credential_client_id = None
    credential_client_secret = None
    data_collection_rule_id = None
    stream_name = None
    auth_mechanism = None

    log_analytics_client = None

    plugin_config_jsonschema = {
        "$schema": "http://json-schema.org/draft/2019-09/schema#",
        "$ref": "#/definitions/PluginConfiguration",
        "definitions": {
            "PluginConfiguration": {
                "type": "object",
                "properties": {
                    "log_ingestion_endpoint": {"type": "string"},
                    "data_collection_rule_id": {"type": "string"},
                    "credential_tenant_id": {"type": "string"},
                    "credential_client_id": {"type": "string"},
                    "credential_client_secret": {"type": "string"},
                },
                "required": ["log_ingestion_endpoint", "data_collection_rule_id"],
            },
        },
    }

    def __init__(self, app_configuration: QueryDict, plugin_configuration: QueryDict):
        """Constructor."""
        super().__init__(app_configuration, plugin_configuration)

        self.log_ingestion_endpoint = plugin_configuration.get("log_ingestion_endpoint")
        self.user_assigned_managed_identity_client_id = app_configuration.get(
            "user_assigned_managed_identity_client_id"
        )
        self.credential_tenant_id = plugin_configuration.get("credential_tenant_id")
        self.credential_client_id = plugin_configuration.get("credential_client_id")
        self.credential_client_secret = plugin_configuration.get("credential_client_secret")

        self.auth_mechanism = "DefaultAzureCredential"
        if self.credential_tenant_id and self.credential_client_id and self.credential_client_secret:
            self.auth_mechanism = "ClientSecretCredential"
        elif self.user_assigned_managed_identity_client_id:
            self.auth_mechanism = "UserAssignedManagedIdentityCredential"

        self.data_collection_rule_id = plugin_configuration.get("data_collection_rule_id")
        self.stream_name = "Custom-AzureOpenAIUsage_PP_CL"

    def on_plugin_instantiated(self):
        """Run directly after the new plugin instance has been instantiated."""
        super().on_plugin_instantiated()

        # get credentials for Log Analytics client
        credential = None
        match self.auth_mechanism:
            case "ClientSecretCredential":
                credential = ClientSecretCredential(
                    tenant_id=self.credential_tenant_id,
                    client_id=self.credential_client_id,
                    client_secret=self.credential_client_secret,
                )
            case "UserAssignedManagedIdentityCredential":
                credential = ManagedIdentityCredential(client_id=self.user_assigned_managed_identity_client_id)
            case _:
                credential = DefaultAzureCredential()

        # get Log Analytics client
        self.log_analytics_client = LogsIngestionClient(
            endpoint=self.log_ingestion_endpoint,
            credential=credential,
            logging_enable=True,
        )

    def on_print_configuration(self):
        """Print plugin-specific configuration."""
        super().on_print_configuration()

        Configuration.print_setting("Log ingestion endpoint", self.log_ingestion_endpoint, 1)
        Configuration.print_setting("Data Collection Rule ID", self.data_collection_rule_id, 1)
        Configuration.print_setting("Authentication mechanism", self.auth_mechanism, 1)
        match self.auth_mechanism:
            case "ClientSecretCredential":
                Configuration.print_setting("Credential Tenant ID", self.credential_tenant_id, 1)
                Configuration.print_setting("Credential Client ID", self.credential_client_id, 1)
            case "UserAssignedManagedIdentityCredential":
                Configuration.print_setting(
                    "User-Assigned Managed Credential ID", self.user_assigned_managed_identity_client_id, 1
                )

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
        aoai_virtual_deployment,
        aoai_standin_deployment,
        aoai_api_version,
    ):
        """Append a new line with the given infos."""
        # pylint: disable=no-value-for-parameter
        self.log_analytics_client.upload(
            rule_id=self.data_collection_rule_id,
            stream_name=self.stream_name,
            logs=[
                {
                    "Client": client,
                    "RequestReceivedUtc": f"{request_received_utc}",
                    "IsStreaming": is_streaming,
                    "PromptTokens": prompt_tokens,
                    "CompletionTokens": completion_tokens,
                    "TotalTokens": total_tokens,
                    "AoaiRoundtripTimeMS": aoai_roundtrip_time_ms,
                    "AoaiRegion": aoai_region,
                    "AoaiEndpoint": aoai_endpoint,
                    "AoaiVirtualDeployment": aoai_virtual_deployment,
                    "AoaiStandinDeployment": aoai_standin_deployment,
                    "AoaiApiVersion": aoai_api_version,
                }
            ],
        )
        # pylint: enable=no-value-for-parameter
