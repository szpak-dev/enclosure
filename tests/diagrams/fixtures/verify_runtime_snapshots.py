import json
from collections import Counter
from hashlib import sha256
from io import StringIO

from django.core.management import call_command
from mermaiden import Application

output = StringIO()
call_command(
    "dumpdata",
    "diagrams.diagram",
    "projects.architecturecontractdiagram",
    "projects.architecturecontractpublication",
    "projects.architecturecontractunit",
    stdout=output,
)
documents = json.loads(output.getvalue())
counts = Counter()
versions = Counter()
losses = Counter()
archives = []
with Application.create() as application:
    for document in documents:
        model = document["model"]
        counts[model] += 1
        if model.startswith("projects."):
            archives.append(document)
        if model not in {"diagrams.diagram", "projects.architecturecontractdiagram"}:
            continue
        snapshot = document["fields"]["snapshot"]
        versions[f"{model}:v{snapshot['version']}"] += 1
        upgraded = application.upgrade_snapshot(snapshot, allow_loss=True)
        for change in upgraded.changes:
            if change.requires_loss_acceptance:
                losses[f"{model}:{change.description}"] += 1
archives.sort(key=lambda document: (document["model"], document["pk"]))
print(
    json.dumps(
        {
            "counts": counts,
            "versions": versions,
            "accepted_losses": losses,
            "archive_evidence_digest": sha256(
                json.dumps(archives, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        },
        sort_keys=True,
    )
)
