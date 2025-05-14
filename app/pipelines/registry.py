import logging
from typing import Dict, Type
from api.event_schema import EventSchema
from core.pipeline import Pipeline
from pipelines.customer_pipeline import CustomerSupportPipeline
from pipelines.internal_pipeline import InternalHelpdeskPipeline


"""
Pipeline Registry Module

This module provides a registry system for managing different pipeline types
and their mappings. It determines which pipeline to use based on event attributes,
currently using email addresses as the routing mechanism.
"""


class PipelineRegistry:
    """Registry for managing and routing to different pipeline implementations.

    This class maintains a mapping of pipeline types to their implementations and
    provides logic for determining which pipeline to use based on event attributes.
    It implements a simple factory pattern for pipeline instantiation.

    Attributes:
        pipelines: Dictionary mapping pipeline type strings to pipeline classes
    """

    pipelines: Dict[str, Type[Pipeline]] = {
        "support": CustomerSupportPipeline,
        "helpdesk": InternalHelpdeskPipeline,
    }

    @staticmethod
    def get_pipeline_type(event: EventSchema) -> str:
        """
        Implement your logic to determine the pipeline type based on the event.
        We're currently using the email address to determine the pipeline type.
        The options are "support" (CustomerSupportPipeline) and
        "helpdesk" (InternalHelpdeskPipeline)
        """
        return event.to_email.split("@")[0]

    @staticmethod
    def get_pipeline(event: EventSchema) -> Pipeline:
        """Creates and returns the appropriate pipeline instance for the event.

        Args:
            event: Event schema containing routing information

        Returns:
            Instantiated pipeline object for processing the event
        """
        pipeline_type = PipelineRegistry.get_pipeline_type(event)
        pipeline = PipelineRegistry.pipelines.get(pipeline_type)
        if pipeline:
            logging.info(f"Using pipeline: {pipeline.__name__}")
            return pipeline()
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")
