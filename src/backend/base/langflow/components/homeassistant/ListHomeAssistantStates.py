import json
from typing import Any, Union

import requests
from pydantic import BaseModel, Field

from langflow.base.langchain_utilities.model import LCToolComponent
from langflow.field_typing import Tool
from langflow.inputs import SecretStrInput, StrInput
from langflow.schema import Data
from langchain.tools import StructuredTool


class ListHomeAssistantStates(LCToolComponent):
    display_name: str = "List HomeAssistant States"
    description: str = (
        "Retrieve states from Home Assistant. "
        "The agent only needs to specify 'filter_domain' (optional). "
        "Token and base_url are not exposed to the agent."
    )
    documentation: str = "https://developers.home-assistant.io/docs/api/rest/"
    icon = "HomeAssistant"

    # 1) Define fields to be received in LangFlow UI
    inputs = [
        SecretStrInput(
            name="ha_token",
            display_name="Home Assistant Token",
            info="Home Assistant Long-Lived Access Token",
            required=True,
        ),
        StrInput(
            name="base_url",
            display_name="Home Assistant URL",
            info="e.g., http://192.168.0.10:8123",
            required=True,
        ),
        StrInput(
            name="filter_domain",
            display_name="Default Filter Domain (Optional)",
            info="light, switch, sensor, etc. (Leave empty to fetch all)",
            required=False,
        ),
    ]

    # 2) Pydantic schema containing only parameters exposed to the agent
    class ToolSchema(BaseModel):
        filter_domain: str = Field("", description="Filter domain (e.g., 'light'). If empty, returns all.")

    def run_model(self) -> Data:
        """
        LangFlow component execution:
        - Uses self.ha_token, self.base_url, self.filter_domain as entered in the UI.
        - Triggered when 'Run' is clicked directly without an agent.
        """
        filter_domain = self.filter_domain or ""  # Use "" for fetching all states
        result = self._list_states(
            ha_token=self.ha_token,
            base_url=self.base_url,
            filter_domain=filter_domain,
        )
        return self._make_data_response(result)

    def build_tool(self) -> Tool:
        """
        Tool object to be used by the agent. In this case:
        - The agent can only pass 'filter_domain' as a parameter.
        - 'ha_token' and 'base_url' are not exposed (stored as self attributes).
        """
        return StructuredTool.from_function(
            name="list_homeassistant_states",
            description=(
                "Retrieve states from Home Assistant. "
                "You can provide filter_domain='light', 'switch', etc. to narrow results."
            ),
            func=self._list_states_for_tool,  # Wrapper function below
            args_schema=self.ToolSchema,      # Requires only filter_domain
        )

    def _list_states_for_tool(self, filter_domain: str = "") -> Union[list[Any], str]:
        """
        Method used when the agent calls the Tool.
        'ha_token' and 'base_url' are stored in self (not exposed).
        """
        return self._list_states(
            ha_token=self.ha_token,
            base_url=self.base_url,
            filter_domain=filter_domain,
        )

    def _list_states(
        self,
        ha_token: str,
        base_url: str,
        filter_domain: str = "",
    ) -> Union[list[Any], str]:
        """
        Calls the actual Home Assistant /api/states endpoint (sensitive info passed directly as arguments).
        """
        try:
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json",
            }
            url = f"{base_url}/api/states"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            all_states = response.json()
            if filter_domain:
                filtered = [
                    st for st in all_states
                    if st.get("entity_id", "").startswith(f"{filter_domain}.")
                ]
                return filtered
            return all_states

        except requests.exceptions.RequestException as e:
            return f"Error: Failed to fetch states. {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"

    def _make_data_response(self, result: Union[list[Any], str, dict]) -> Data:
        """
        Helper method to format the response into a Data object.
        """
        try:
            if isinstance(result, list):
                # Wrap list data into a dictionary and convert to text
                wrapped_result = {"result": result}
                return Data(
                    data=wrapped_result,
                    text=json.dumps(wrapped_result, indent=2, ensure_ascii=False)
                )
            elif isinstance(result, dict):
                # Return dictionary as-is
                return Data(
                    data=result,
                    text=json.dumps(result, indent=2, ensure_ascii=False)
                )
            elif isinstance(result, str):
                # Return error messages or strings
                return Data(data={}, text=result)
            else:
                # Handle unexpected data types
                return Data(
                    data={},
                    text="Error: Unexpected response format."
                )
        except Exception as e:
            # Handle exceptions during formatting
            return Data(
                data={},
                text=f"Error: Failed to process response. Details: {str(e)}"
            )