import subprocess
import os

port = os.environ.get("PORT", "4000")
subprocess.run([
    "litellm",
    "--config", "litellm.yaml",
    "--port", port,
    "--host", "0.0.0.0"
])
