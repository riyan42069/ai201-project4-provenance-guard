import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from signals import burstiness_score, stylometric_score, combine_scores, generate_label
from audit import write_entry, find_entry, update_entry, read_log

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)


def get_appeal_key():
    data = request.get_json(force=True, silent=True) or {}
    return data.get("creator_id") or get_remote_address()


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    creator_id = (data.get("creator_id") or "").strip()

    if not text or not creator_id:
        return jsonify({"error": "text and creator_id are required"}), 400

    content_id = str(uuid.uuid4())
    b_score = burstiness_score(text)
    s_score = stylometric_score(text)
    confidence = combine_scores(b_score, s_score)
    verdict, label_text = generate_label(confidence)

    entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "text_length": len(text),
        "burstiness_score": b_score,
        "stylometric_score": s_score,
        "confidence_score": confidence,
        "verdict": verdict,
        "label_text": label_text,
        "status": "classified"
    }

    write_entry(entry)

    return jsonify({
        "content_id": content_id,
        "attribution": verdict,
        "confidence": confidence,
        "label": label_text,
        "signals": {
            "burstiness": b_score,
            "stylometric": s_score
        }
    })


@app.route("/appeal", methods=["POST"])
@limiter.limit("3 per hour", key_func=get_appeal_key)
def appeal():
    data = request.get_json(force=True)
    content_id = (data.get("content_id") or "").strip()
    creator_reasoning = (data.get("creator_reasoning") or "").strip()

    if not content_id or not creator_reasoning:
        return jsonify({"error": "content_id and creator_reasoning are required"}), 400

    entry = find_entry(content_id)
    if not entry:
        return jsonify({"error": "content_id not found"}), 404

    if entry.get("appeal_reason"):
        return jsonify({"error": "an appeal already exists for this content_id"}), 409

    updated = update_entry(content_id, {
        "status": "under_review",
        "appeal_reason": creator_reasoning,
        "appealed_at": datetime.now(timezone.utc).isoformat(),
    })

    if not updated:
        return jsonify({"error": "failed to update log entry"}), 500

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Your appeal has been received. This content has been marked for human review."
    })


@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": read_log()})


if __name__ == "__main__":
    app.run(debug=True)
