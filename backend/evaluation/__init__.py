"""
LangSmith Evaluation for WordAgent

This module provides evaluation functionality using LangSmith datasets.
"""

from .dataset import fetch_dataset
from .run import run_evaluation

__all__ = ["fetch_dataset", "run_evaluation"]
