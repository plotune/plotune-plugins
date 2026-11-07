---
name: plotune-artifacts-drives
description: Use when listing, reading, downloading, exporting, importing, uploading, deleting, or cleaning up Plotune Nexus artifacts, or when accessing configured artifact drives such as local storage, SFTP, Google Drive, or OneDrive.
---

# Plotune Nexus Artifacts And Drives

Large outputs belong in artifacts or configured drives, not inline MCP responses. Always inspect artifact metadata before reusing paths.

## Step 1 — Find Artifacts

**Quick overview from the last 2 hours:**
```
read resource: plotune://artifacts/recent
```

**Full artifact list:**
```
list_artifacts_tool()
list_artifacts_tool(only_complete=True)
list_artifacts_tool(job_id="<recording-or-test-sequence-job-id>", limit=20)
```

Use `job_id` with a recording job ID to filter that recording's artifact, or with a test-sequence job ID to list artifacts related to that sequence.

**Get path and format for a specific artifact:**
```
get_artifact_metadata_tool(artifact_id="<artifact-id>")
```

Strip any `/host/` prefix from the returned path before using it in other tool calls:
```
/host/var/lib/plotune-nexus/recordings/run.mf4  →  /var/lib/plotune-nexus/recordings/run.mf4
```

## Step 2 — Read Artifact Content Inline

For small or text artifacts, read a bounded slice without exporting:
```
read_artifact(artifact_id="<artifact-id>", max_bytes=65536)
```

Each read returns at most 256 KiB and sets `next_offset` until `eof`. To look at part of a big file without paging, use `from_end=True` for the tail or `start_line=N` to start at a line of a text file. Do not use inline reads for large binary files: inspect `bytes_size` from metadata first and download the file with `get_artifact` instead.

## Step 3 — Export An Artifact (Download URL)

Get a download URL for the artifact:
```
get_artifact(artifact_id="<artifact-id>", folder_name="artifacts")
```

The file is served straight from the device (`transport: "direct"`) at any size, with no cloud or internet needed. Download the URL outside MCP with `curl -fL -C - -o "<file_name>" "<download_url>"` (resumable; use the `file_name` from the result) or a browser. A direct link needs no auth header and stays valid while it is being used, up to a few hours. Use `mode="cloud"` to get a Plotune transfer cloud link instead (for example to share with someone who cannot reach the device). For OCI container images, use `folder_name="containers"`.

## Step 4 — Import An Artifact (Two-Phase Upload)

Importing a file into Nexus is a two-step process:

**Step 4a — Prepare and get an upload URL:**
```
prepare_put_artifact(
  file_name="network.dbc",
  size=20480,
  sha256="<sha256-hex-of-file>",
  content_type="application/octet-stream",
  folder_name="artifacts"
)
```

**Step 4b — Upload the file bytes with `PUT <upload_url>` (outside MCP, using the client's HTTP client, e.g. `curl --upload-file network.dbc "<upload_url>"`, no extra headers).** Uploads go directly to the device at any size (`transport: "direct"`). On the local network one request carries the whole file. Through the device tunnel one request is capped at 64 MiB, so send bigger files as pieces of up to 32 MiB with a `Content-Range: bytes <start>-<end>/<size>` header; a wrong-offset piece is refused with the byte count to resume from. The link stays valid while pieces keep arriving and expires after 15 minutes of silence. See the tool contracts for a ready-made shell loop. Use `mode="cloud"` to upload through the Plotune transfer cloud instead.

**Step 4c — Confirm the import and read the device path:**
```
put_artifact(transfer_id="<transfer-id-from-prepare>")
```

For OCI container image tars, use `folder_name="containers"` in Step 4a.

## Step 5 — Artifact Drives

Configured drives extend artifact storage to external systems. List available drives:
```
list_artifact_drives()
```

**Browse drive contents:**
```
list_drive_content(drive_id="<drive-id>", remote_path="bench-runs/", recursive=False, limit=100)
```

SFTP drives do not support recursive listing — browse folder by folder.

**Search within a drive:**
```
search_in_drive(drive_id="<drive-id>", query="run.mf4", remote_path="", limit=50)
```

**Download from a drive to the Nexus device:**
```
download_from_artifact_drive(
  drive_id="<drive-id>",
  remote_path="bench-runs/run.mf4",
  local_path="/var/lib/plotune-nexus/recordings/run.mf4",
  overwrite=False
)
```

`local_path` is a Nexus-device path. Omit it to let the tool choose a default location.

**Upload from the Nexus device to a drive:**
```
upload_to_artifact_drive(
  drive_id="<drive-id>",
  local_path="/var/lib/plotune-nexus/recordings/run.mf4",
  remote_path="bench-runs/run.mf4",
  overwrite=False
)
```

Drive `remote_path` is relative to the configured drive root. Use `bench-runs/run.mf4`, not `shared/bench-runs/run.mf4`.

## Step 6 — Delete An Artifact

Deletion is permanent. Require the operator to confirm the exact artifact ID before calling:
```
delete_artifact_tool(artifact_id="<artifact-id>")
```

Do not delete artifacts proactively. Only call this after explicit operator confirmation.

## Step 7 — Retention Cleanup

Always run a dry run first and summarize the result before deleting:
```
run_artifact_cleanup(dry_run=True)
```

Show the user `deleted_count` and `deleted_paths` from the dry-run result. Only proceed after explicit operator confirmation:
```
run_artifact_cleanup(dry_run=False)
```

## Routing Exported Artifacts Through Offline Analysis

After downloading a recording or artifact to the workstation, use the offline scripts for analysis:

| Artifact type | Script |
|---|---|
| CAN/ASC/log trace | `python3 scripts/automotive/can_trace_summarize.py --trace path/to/capture.log --dbc path/to/network.dbc --format json` |
| A2L and LAB files | `python3 scripts/automotive/a2l_lab_check.py --a2l path/to/ECM.a2l --lab path/to/measurements.lab --format json` |
| UDS sequence CSV | `python3 scripts/automotive/uds_sequence_lint.py --sequence path/to/sequence.csv --format json` |
| Mixed artifacts | `python3 scripts/automotive/automotive_triage.py --inputs path/to/a path/to/b --format json` |
| Evidence packaging | `python3 scripts/automotive/evidence_pack.py --inputs path/to/report.json path/to/log --classification mixed --format json` |

## Notes

- `plotune://artifacts/recent` covers device-local artifact metadata from the last 2 hours. It is not remote drive history.
- Drive paths are relative to the configured root — do not include the root folder name in `remote_path`.
- SFTP drives do not support recursive listing or search.
- Keep large binary content out of conversational responses unless bounded by the user's explicit request.
