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

class ToolCallingAgent:
    """
    Universal tool calling agent that works on all platforms
    Automatically selects vLLM (if supported and a GPU is available) or Ollama
    """
    def __init__(self, backend: Optional[str] = None):
        """
        Initialize with automatic backend detection

        Args:
            backend: Force a specific backend ('vllm', 'ollama', or None for auto)
        """
        self.agent = None
        self.backend_type = backend or self._detect_best_backend()

        logger.info(f"Initializing on {platform.system()} with {self.backend_type}")
        self._initialize_backend()

    def _detect_best_backend(self) -> str:
        """Detect the best backend for current platform"""
        system = platform.system()

        # Official vLLM GPU execution requires Linux. WSL2 reports itself as
        # Linux here, while native Windows must use Ollama even when PyTorch
        # can see a CUDA-capable GPU.
        if system == "Linux":
            try:
                import torch  # type: ignore
                if torch.cuda.is_available():
                    logger.info("CUDA detected on Linux - will use vLLM")
                    return "vllm"
            except ImportError:
                pass

        if system == "Windows":
            logger.info(
                "Native Windows detected - official vLLM requires Linux; "
                "using Ollama (use WSL2 for vLLM)"
            )
            return "ollama"

        # Default to Ollama for macOS or Linux systems without CUDA
        logger.info(f"Using Ollama on {system}")
        return "ollama"

    def _initialize_backend(self):
        """Initialize the selected backend"""
        if self.backend_type == "vllm":
            self._init_vllm()
        else:
            self._init_ollama()

    def _init_vllm(self):
        """Initialize vLLM backend"""
        try:
            # Check if vLLM server is running
            import requests
            from config import VLLM_HOST, VLLM_PORT

            server_url = f"http://{VLLM_HOST}:{VLLM_PORT}/health"

            try:
                response = requests.get(server_url, timeout=1)
                if response.status_code != 200:
                    raise ConnectionError("vLLM server not responding")
            except Exception:
                # Try to start the server
                logger.info("Starting vLLM server...")
                from server import VLLMServer
                server = VLLMServer()
                server.start(wait_for_ready=True)

            # Initialize vLLM agent
            from agent import VLLMToolAgent
            from config import OPENAI_API_BASE, OPENAI_API_KEY

            self.agent = VLLMToolAgent(
                api_base=OPENAI_API_BASE,
                api_key=OPENAI_API_KEY
            )
            logger.info("✅ vLLM agent initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize vLLM: {e}")
            logger.info("Falling back to Ollama")
            self.backend_type = "ollama"
            self._init_ollama()

    def _init_ollama(self):
        """Initialize Ollama backend"""
        try:
            import ollama # type: ignore
            from ollama_native import OllamaNativeAgent

            # Check if Ollama is running
            client = ollama.Client()
            try:
                models_response = client.list()
                available_models = []
                if hasattr(models_response, 'models'):
                    available_models = [m.model for m in models_response.models]

                if not available_models:
                    logger.error("No Ollama models installed")
                    logger.info("Install a model with: ollama pull qwen3:0.6b")
                    sys.exit(1)

                # Use qwen3:0.6b as the default model
                model = "qwen3:0.6b"

                # Check if qwen3:0.6b is available
                if model not in available_models:
                    logger.warning(f"Recommended model {model} not found in available models")
                    logger.info("Install with: ollama pull qwen3:0.6b")
                    # Fall back to first available model if qwen3:0.6b is not installed
                    model = available_models[0]
                    logger.info(f"Using fallback model: {model}")

                logger.info(f"Using Ollama model: {model}")
                self.agent = OllamaNativeAgent(model=model)

            except Exception as e:
                logger.error(f"Ollama is not running: {e}")
                logger.info("\nPlease start Ollama:")

                system = platform.system()
                if system == "Darwin":  # Mac
                    logger.info("  brew services start ollama")
                    logger.info("  or: ollama serve")
                elif system == "Windows":
                    logger.info("  Start Ollama from the system tray")
                    logger.info("  or run: ollama serve")
                else:  # Linux
                    logger.info("  systemctl start ollama")
                    logger.info("  or: ollama serve")

                sys.exit(1)

        except ImportError:
            logger.error("Ollama not installed")
            logger.info("Install with: pip install ollama")
            sys.exit(1)

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

    # Header
    print("="*60)
    print("🚀 Universal Tool Calling Agent")
    print("="*60)

    # Show system info if requested
    if args.info:
        print("\n📊 System Information:")
        print(f"  Platform: {platform.system()} {platform.release()}")
        print(f"  Architecture: {platform.machine()}")
        print(f"  Python: {sys.version.split()[0]}")

        # Check CUDA
        try:
            import torch # type: ignore
            cuda_available = torch.cuda.is_available()
            if cuda_available:
                print(f"  CUDA: ✅ Available (GPU: {torch.cuda.get_device_name(0)})")
            else:
                print("  CUDA: ❌ Not available")
        except ImportError:
            print("  CUDA: ❌ PyTorch not installed")

        # Check Ollama
        try:
            import ollama # type: ignore
            print("  Ollama: ✅ Package installed")
        except ImportError:
            print("  Ollama: ❌ Package not installed")

        return 0

    # Initialize agent
    print("\n⚙️  Initializing agent...")
    backend = None if args.backend == "auto" else args.backend

    return 0

if __name__=="__main__":
    sys.exit(main())
