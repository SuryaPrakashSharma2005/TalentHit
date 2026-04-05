import subprocess
import tempfile
import os
import resource
import signal

# ======================================================
# CONFIG
# ======================================================

MAX_OUTPUT_SIZE = 10000
EXECUTION_TIMEOUT = 3  # stricter timeout

# Resource limits
MAX_MEMORY = 64 * 1024 * 1024  # 64 MB
MAX_CPU_TIME = 2  # seconds


# ======================================================
# RESOURCE LIMITER (CRITICAL)
# ======================================================

def limit_resources():
    """
    Restrict memory, CPU and prevent abuse
    """
    try:
        # Limit memory (Address Space)
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))

        # Limit CPU time
        resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_TIME, MAX_CPU_TIME))

        # Prevent fork bombs
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))

        # Disable file size writes
        resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))

    except Exception:
        pass


# ======================================================
# MAIN EXECUTOR
# ======================================================

def run_python_code(source_code: str, input_data: str):
    """
    Secure execution of user Python code.

    Returns:
        {
            stdout: str,
            stderr: str,
            returncode: int
        }
    """

    file_path = None

    try:
        # ------------------------------
        # CREATE TEMP FILE
        # ------------------------------
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".py",
            mode="w",
            encoding="utf-8"
        ) as temp_file:
            file_path = temp_file.name
            temp_file.write(source_code)

        # ------------------------------
        # RUN PROCESS (ISOLATED MODE)
        # ------------------------------
        process = subprocess.run(
            ["python3", "-I", "-u", file_path],  # 🔒 isolated mode
            input=input_data,
            text=True,
            capture_output=True,
            timeout=EXECUTION_TIMEOUT,
            preexec_fn=limit_resources  # 🔒 enforce limits
        )

        stdout = (process.stdout or "").strip()
        stderr = (process.stderr or "").strip()

        # ------------------------------
        # OUTPUT LIMIT
        # ------------------------------
        if len(stdout) > MAX_OUTPUT_SIZE:
            stdout = stdout[:MAX_OUTPUT_SIZE]

        if len(stderr) > MAX_OUTPUT_SIZE:
            stderr = stderr[:MAX_OUTPUT_SIZE]

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode
        }

    # ------------------------------
    # TIMEOUT HANDLING
    # ------------------------------
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Execution timed out",
            "returncode": -1
        }

    # ------------------------------
    # GENERIC ERROR
    # ------------------------------
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1
        }

    # ------------------------------
    # CLEANUP
    # ------------------------------
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass