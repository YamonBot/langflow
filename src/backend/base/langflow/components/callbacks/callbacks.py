from langchain.callbacks.base import BaseCallbackHandler

from langflow.custom import Component
from langflow.template import Output


class CallbacksComponent(Component):
    """Expose Langchain callback handlers as a component output."""

    display_name = "Callbacks"
    description = "Return callbacks from the tracing service so they can be connected via handles."
    name = "Callbacks"
    icon = "Share"

    outputs = [
        Output(display_name="Callbacks", name="callbacks", method="build_callbacks", types=["Callbacks"])
    ]

    def build_callbacks(self) -> list[BaseCallbackHandler]:
        return self.get_langchain_callbacks()
