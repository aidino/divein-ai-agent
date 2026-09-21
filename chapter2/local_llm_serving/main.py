from ast import parse
import os
from posixpath import pardir
import sys
import platform
import logging
from typing import Optional, Dict, Any, List
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description= "Universal(Phổ quát) Tool Calling Agent - Work on all platform"
    )
    parser.add_argument(
        "--mode",
        choices=["single", "interactive"],
        default="interactive",
        help="Execution mode (default: interactive)"
    )
    parser.add_argument(
        "--task",
        type=str,
        help="Task to execute (for single mode)"
    )
    parser.add_argument(
        "--backend",
        choices=["vllm", "ollama", "auto"],
        default="auto",
        help="Backend to use (default: auto-detect)"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show system infomation and exit"
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        default=True,
        help="Enable streaming mode (default: True)"
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming mode"
    )

    args = parser.parse_args()




    return 0

if __name__=="__main__":
    sys.exit(main())
