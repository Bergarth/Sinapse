"""Runtime loading for shared gRPC contracts."""

from __future__ import annotations

import importlib
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_contract_modules() -> tuple[object, object]:
    """Compile and import the shared proto contract modules.

    This keeps `packages/contracts` as the single source of truth.
    """

    repo_root = Path(__file__).resolve().parents[4]
    proto_root = repo_root / "packages" / "contracts" / "src"
    proto_file = proto_root / "sinapse" / "contracts" / "v1" / "contracts.proto"

    out_dir = Path(tempfile.gettempdir()) / "sinapse_contracts_py"
    out_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{proto_root}",
            f"--python_out={out_dir}",
            f"--grpc_python_out={out_dir}",
            str(proto_file),
        ],
        check=True,
    )

    if str(out_dir) not in sys.path:
        sys.path.insert(0, str(out_dir))

    pb2 = importlib.import_module("sinapse.contracts.v1.contracts_pb2")
    pb2_grpc = importlib.import_module("sinapse.contracts.v1.contracts_pb2_grpc")
    return pb2, pb2_grpc
