from typing import Dict
from bson import ObjectId


async def evaluate_mcqs(db, answers: Dict[str, int]) -> Dict[str, float]:
    """
    Evaluate answers against `assessment_questions`.

    `answers` map: question_id (str) -> selected option index (int)
    We fetch the original question docs and determine correct answer id,
    then map that id to the provided shuffled options using the snapshot
    index supplied by the caller. If a mapping cannot be resolved, it's
    treated as incorrect.
    """

    if not answers:
        return {"total_questions": 0, "correct_answers": 0, "mcq_score": 0.0}

    # convert keys to ObjectId where possible
    obj_ids = []
    id_map = {}
    for qid in answers.keys():
        try:
            oid = ObjectId(qid)
            obj_ids.append(oid)
            id_map[str(oid)] = qid
        except:
            # skip invalid ids
            continue

    docs = []
    if obj_ids:
        docs = await db["assessment_questions"].find({"_id": {"$in": obj_ids}}).to_list(length=len(obj_ids))

    total = 0
    correct = 0

    for doc in docs:
        qid_str = str(doc.get("_id"))
        # caller supplied selected index based on a snapshot's options
        selected_index = answers.get(id_map.get(qid_str, qid_str))
        if selected_index is None:
            continue

        # reconstruct options as list of ids in original order
        options = [o.get("id") for o in doc.get("options", [])]
        # determine if selected index maps to correct_answer
        try:
            selected_id = options[int(selected_index)]
        except Exception:
            selected_id = None

        total += 1
        if selected_id and selected_id == doc.get("correct_answer"):
            correct += 1

    score = (correct / total) * 100 if total else 0

    return {"total_questions": total, "correct_answers": correct, "mcq_score": round(score, 2)}
