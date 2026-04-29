"""
Fetch and inspect LangSmith dataset.

Usage:
    python -m evaluation.fetch_dataset
"""

import os
import json
from typing import Optional

from dotenv import load_dotenv
from langsmith import Client as LangSmithClient

load_dotenv()

# Configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
DATASET_NAME = os.getenv("LANGSMITH_DATASET_NAME", "WordAgent_test")


def fetch_dataset(dataset_name: str = DATASET_NAME, output_path: Optional[str] = None):
    """
    Fetch dataset from LangSmith and optionally save to file.

    Args:
        dataset_name: Name of the dataset to fetch
        output_path: Optional path to save dataset as JSON
    """
    client = LangSmithClient(api_key=LANGSMITH_API_KEY)

    print(f"Connecting to LangSmith...")
    print(f"  API Key: {'*' * 20}{LANGSMITH_API_KEY[-10:] if LANGSMITH_API_KEY else 'NOT SET'}")
    print()

    # Get dataset
    print(f"Fetching dataset: {dataset_name}")

    try:
        # Use client.read_dataset() or filter from list_datasets
        dataset = None
        for ds in client.list_datasets(dataset_name=dataset_name):
            dataset = ds
            break
        if dataset is None:
            raise ValueError(f"Dataset '{dataset_name}' not found")
    except Exception as e:
        print(f"Error: Could not find dataset '{dataset_name}'")
        print(f"  {e}")
        print()
        print("Available datasets:")
        for ds in client.list_datasets():
            print(f"  - {ds.name}: {ds.description or 'No description'}")
        return

    print(f"\nDataset Details:")
    print(f"  ID: {dataset.id}")
    print(f"  Name: {dataset.name}")
    print(f"  Description: {dataset.description or 'No description'}")
    print(f"  Created: {dataset.created_at}")
    print()

    # Get all examples using the correct API
    examples = list(client.list_examples(dataset_id=dataset.id))

    print(f"Number of examples: {len(examples)}")
    print()

    if not examples:
        print("No examples found. Please add examples to your dataset in LangSmith.")
        return

    # Display examples
    print("=" * 60)
    print("EXAMPLES")
    print("=" * 60)

    dataset_data = {
        "dataset_id": str(dataset.id),
        "dataset_name": dataset.name,
        "description": dataset.description,
        "examples": [],
    }

    for i, example in enumerate(examples):
        print(f"\n--- Example {i + 1} ---")
        print(f"ID: {example.id}")
        print(f"Inputs:")
        for key, value in example.inputs.items():
            if isinstance(value, str) and len(value) > 200:
                print(f"  {key}: {value[:200]}...")
            else:
                print(f"  {key}: {value}")

        if example.outputs:
            print(f"Outputs (Expected):")
            for key, value in example.outputs.items():
                if isinstance(value, str) and len(value) > 200:
                    print(f"  {key}: {value[:200]}...")
                else:
                    print(f"  {key}: {value}")

        if example.metadata:
            print(f"Metadata: {example.metadata}")

        # Store for JSON export
        example_data = {
            "id": str(example.id),
            "inputs": example.inputs,
            "outputs": example.outputs,
            "metadata": example.metadata,
        }
        dataset_data["examples"].append(example_data)

    # Save to JSON if path provided
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset_data, f, ensure_ascii=False, indent=2)
        print(f"\nDataset saved to: {output_path}")

    return dataset, examples


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fetch dataset from LangSmith")
    parser.add_argument("--name", "-n", default=DATASET_NAME, help="Dataset name")
    parser.add_argument("--output", "-o", help="Output JSON file path (optional)")

    args = parser.parse_args()

    print("=" * 60)
    print("LangSmith Dataset Fetcher")
    print("=" * 60)
    print()

    fetch_dataset(args.name, args.output)


if __name__ == "__main__":
    main()
