from typing import Dict, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .executor import run_python_code


# ======================================================
# CONFIG
# ======================================================

MAX_WORKERS = 4  # parallel execution limit


# ======================================================
# NORMALIZATION
# ======================================================

def normalize_output(text: str) -> str:
    if text is None:
        return ""

    return "\n".join(
        line.strip() for line in str(text).strip().splitlines()
    )


# ======================================================
# SINGLE TEST EXECUTION
# ======================================================

def run_single_test(user_code: str, test: Dict) -> bool:
    input_data = test.get("input", "")
    expected_output = normalize_output(test.get("output", ""))

    try:
        result = run_python_code(user_code, input_data)

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        if stderr:
            return False

        output = normalize_output(stdout)

        return output.strip().lower() == expected_output.strip().lower()

    except Exception:
        return False


# ======================================================
# MAIN EVALUATOR (PARALLEL)
# ======================================================

async def evaluate_solution(question: Dict, user_code: str) -> float:
    """
    Production-grade evaluator:
    - Parallel execution
    - Hidden test weighting
    - Early stopping
    """

    visible_tests: List[Dict] = question.get("test_cases", [])
    hidden_tests: List[Dict] = question.get("hidden_test_cases", [])

    if not visible_tests and not hidden_tests:
        return 0.0

    loop = asyncio.get_event_loop()

    # =====================================
    # THREAD POOL (NON-BLOCKING)
    # =====================================

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:

        # ---------------------------------
        # RUN VISIBLE TESTS FIRST
        # ---------------------------------

        visible_tasks = [
            loop.run_in_executor(executor, run_single_test, user_code, test)
            for test in visible_tests
        ]

        visible_results = await asyncio.gather(*visible_tasks)

        visible_passed = sum(visible_results)
        visible_total = len(visible_tests)

        # 🚨 EARLY REJECTION (ANTI CHEAT / FAST FAIL)
        if visible_total > 0 and visible_passed == 0:
            return 0.0

        # ---------------------------------
        # RUN HIDDEN TESTS
        # ---------------------------------

        hidden_tasks = [
            loop.run_in_executor(executor, run_single_test, user_code, test)
            for test in hidden_tests
        ]

        hidden_results = await asyncio.gather(*hidden_tasks)

        hidden_passed = sum(hidden_results)
        hidden_total = len(hidden_tests)

    # =====================================
    # WEIGHTED SCORING
    # =====================================

    visible_score = (
        (visible_passed / visible_total) * 50
        if visible_total > 0 else 0
    )

    hidden_score = (
        (hidden_passed / hidden_total) * 50
        if hidden_total > 0 else 0
    )

    final_score = visible_score + hidden_score

    return round(final_score, 2)

    print("EXPECTED:", expected_output)
    print("GOT:", output)