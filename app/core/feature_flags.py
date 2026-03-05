"""
Feature flags for gradual migration from CF Workers v1 → FastAPI v2.
Each module can be toggled independently.
"""

from app.settings import settings


class FeatureFlags:
    @staticmethod
    def is_v2_intake() -> bool:
        return settings.v2_intake

    @staticmethod
    def is_v2_rfqs() -> bool:
        return settings.v2_rfqs

    @staticmethod
    def is_v2_traceability() -> bool:
        return settings.v2_traceability

    @staticmethod
    def is_v2_suppliers() -> bool:
        return settings.v2_suppliers

    @staticmethod
    def is_v2_document_upload() -> bool:
        return settings.v2_document_upload

    @staticmethod
    def is_dataroom_enabled() -> bool:
        return settings.dataroom_enabled
