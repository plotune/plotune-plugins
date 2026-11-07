#!/usr/bin/env python3
"""Behavior tests for offline automotive helper scripts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts" / "automotive"
FIXTURES = ROOT / "tests" / "fixtures"


def run_json(script: str, *args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args, "--format", "json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return json.loads(completed.stdout)


class AutomotiveScriptTests(unittest.TestCase):
    def test_cli_help_output_and_error_contracts(self) -> None:
        for script in (
            "dbc_sanity.py",
            "can_trace_summarize.py",
            "uds_payload.py",
            "a2l_lab_check.py",
            "autosar_manifest_inspect.py",
            "odx_inspect.py",
            "requirements_trace_lint.py",
            "safety_workproduct.py",
            "tara_workproduct.py",
            "autosar_architecture_report.py",
            "calibration_diff.py",
            "xcp_daq_plan.py",
            "uds_sequence_lint.py",
            "automotive_triage.py",
            "evidence_pack.py",
            "tool_inventory.py",
            "tool_compare.py",
            "inspect_ehb.py",
            "inspect_a2l.py",
        ):
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / script), "--help"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertIn("usage:", completed.stdout)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "dbc.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "dbc_sanity.py"),
                    "--dbc",
                    str(FIXTURES / "sample.dbc"),
                    "--format",
                    "json",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
            )
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["summary"]["messages"], 2)

        missing = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "dbc_sanity.py"),
                "--dbc",
                str(FIXTURES / "missing.dbc"),
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("DBC not found", missing.stderr)

        invalid_hex = subprocess.run(
            [sys.executable, str(SCRIPTS / "uds_payload.py"), "decode", "XX", "--format", "json"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertNotEqual(invalid_hex.returncode, 0)
        self.assertIn("Invalid hex payload", invalid_hex.stderr)

    def test_dbc_sanity_reports_duplicate_frames_and_signal_overlap(self) -> None:
        report = run_json("dbc_sanity.py", "--dbc", str(FIXTURES / "sample.dbc"))

        self.assertEqual(report["summary"]["messages"], 2)
        self.assertIn("0x100", report["issues"]["duplicate_frame_ids"])
        self.assertTrue(report["issues"]["overlapping_signals"])
        self.assertIn("OverlapSignal", report["issues"]["missing_units"])
        self.assertEqual(report["summary"]["can_fd_messages"], 0)

    def test_can_trace_summarize_reports_ids_timing_and_payload_changes(self) -> None:
        report = run_json(
            "can_trace_summarize.py",
            "--trace",
            str(FIXTURES / "sample_trace.log"),
            "--dbc",
            str(FIXTURES / "sample.dbc"),
            "--bitrate",
            "500000",
        )

        self.assertEqual(report["summary"]["frames"], 6)
        self.assertEqual(report["summary"]["remote_frames"], 1)
        self.assertEqual(report["context"]["bitrate"], 500000)
        self.assertEqual(report["context"]["dbc"], str(FIXTURES / "sample.dbc"))
        self.assertTrue(report["context"]["dbc_used_for_decoding"])
        self.assertIn("0x101", report["dbc_coverage"]["observed_ids_missing_from_dbc"])
        self.assertIn("0x100", report["dbc_coverage"]["decoded_ids"])
        self.assertIn("0x100", report["messages"])
        self.assertTrue(report["messages"]["0x100"]["decoded_samples"])
        self.assertEqual(report["messages"]["0x100"]["count"], 3)
        self.assertEqual(report["messages"]["0x100"]["payload_changes"], 1)
        self.assertTrue(report["issues"]["duplicate_dbc_frame_ids"])

        markdown = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "can_trace_summarize.py"),
                "--trace",
                str(FIXTURES / "sample_trace.log"),
                "--dbc",
                str(FIXTURES / "sample.dbc"),
                "--format",
                "markdown",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
        self.assertIn("Decoded Signal Samples", markdown)
        self.assertIn("Unknown Observed IDs", markdown)
        self.assertIn("Duplicate DBC Frame IDs", markdown)

    def test_can_trace_summarize_handles_can_fd_and_muxed_dbc(self) -> None:
        report = run_json(
            "can_trace_summarize.py",
            "--trace",
            str(FIXTURES / "sample_fd_trace.log"),
            "--dbc",
            str(FIXTURES / "sample_fd_mux.dbc"),
            "--bitrate",
            "2000000",
        )

        self.assertEqual(report["summary"]["frames"], 3)
        self.assertEqual(report["summary"]["malformed_lines"], 1)
        self.assertEqual(report["summary"]["can_fd_frames"], 3)
        self.assertEqual(report["issues"]["malformed_lines"][0]["line"], 4)
        self.assertTrue(report["context"]["dbc_used_for_decoding"])
        self.assertIn("0x300", report["dbc_coverage"]["decoded_ids"])
        decoded = report["messages"]["0x300"]["decoded_samples"]
        self.assertEqual(decoded[0]["signals"]["Mode"]["raw"], 1)
        self.assertEqual(decoded[0]["signals"]["SignalA"]["raw"], 16)
        self.assertEqual(decoded[1]["signals"]["Mode"]["raw"], 2)
        self.assertEqual(decoded[1]["signals"]["SignalB"]["raw"], 32)

        markdown = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "can_trace_summarize.py"),
                "--trace",
                str(FIXTURES / "sample_fd_trace.log"),
                "--dbc",
                str(FIXTURES / "sample_fd_mux.dbc"),
                "--format",
                "markdown",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        ).stdout
        self.assertIn("CAN FD frames: 3", markdown)
        self.assertIn("Malformed Lines", markdown)
        self.assertIn("Decoded Signal Samples", markdown)

    def test_can_trace_summarize_vector_canfd_asc_format(self) -> None:
        """Vector CANalyzer/CANoe ASC CAN FD format with CANFD keyword and x-suffixed extended IDs."""
        report = run_json(
            "can_trace_summarize.py",
            "--trace",
            str(FIXTURES / "sample_canfd_asc.asc"),
        )
        self.assertEqual(report["summary"]["frames"], 2, "should parse both CANFD ASC lines")
        self.assertEqual(report["summary"]["malformed_lines"], 0, "header/event lines must not be counted as malformed")
        self.assertEqual(report["summary"]["can_fd_frames"], 2)
        self.assertIn("0x456", report["messages"])
        self.assertIn("0x18FF50E5", report["messages"])
        self.assertEqual(
            report["messages"]["0x456"]["sample_payloads"],
            ["0102030405060708090A0B0C"],
        )
        self.assertEqual(
            report["messages"]["0x18FF50E5"]["sample_payloads"],
            ["101112131415161718191A1B1C1D1E1F"],
        )

    def test_uds_payload_decode_and_build_helpers_are_offline(self) -> None:
        decoded = run_json("uds_payload.py", "decode", "7F2278")
        self.assertEqual(decoded["kind"], "negative_response")
        self.assertEqual(decoded["service"]["id"], "0x22")
        self.assertEqual(decoded["negative_response_code"]["name"], "responsePending")

        request = run_json("uds_payload.py", "rdbi", "F190", "F187")
        self.assertEqual(request["request_hex"], "22F190F187")

        status = run_json("uds_payload.py", "dtc-status", "9B")
        self.assertIn("testFailed", status["set_bits"])
        self.assertIn("confirmedDTC", status["set_bits"])

        vin = run_json("uds_payload.py", "decode", "62F1905756575A5A5A314A5A5857303030303031")
        self.assertEqual(vin["decoded_data_identifiers"][0]["did"], "0xF190")
        self.assertEqual(vin["decoded_data_identifiers"][0]["ascii"], "WVWZZZ1JZXW000001")

    def test_a2l_lab_check_reports_inventory_and_lab_gaps(self) -> None:
        report = run_json(
            "a2l_lab_check.py",
            "--a2l",
            str(FIXTURES / "sample.a2l"),
            "--lab",
            str(FIXTURES / "sample.lab"),
        )

        self.assertEqual(report["summary"]["measurements"], 2)
        self.assertEqual(report["summary"]["characteristics"], 2)
        self.assertEqual(report["summary"]["groups"], 1)
        self.assertEqual(report["summary"]["compu_methods"], 1)
        self.assertEqual(report["summary"]["record_layouts"], 1)
        self.assertIn("IdleSpeedTarget", report["issues"]["duplicate_symbols"])
        self.assertIn("MissingSignal", report["issues"]["lab_symbols_missing_from_a2l"])
        self.assertIn("CoolantTemp", report["issues"]["symbols_missing_units"])
        self.assertTrue(report["xcp_hints"]["mentions_xcp"])
        self.assertEqual(report["memory_ranges"]["min_address"], "0x1000")

        targeted = run_json(
            "inspect_a2l.py",
            "--a2l",
            str(FIXTURES / "sample.a2l"),
            "--symbol",
            "EngineSpeed",
        )
        self.assertEqual(targeted["symbols"]["EngineSpeed"]["measurements"][0]["name"], "EngineSpeed")

    def test_autosar_manifest_inspect_reports_duplicate_names_and_refs(self) -> None:
        report = run_json(
            "autosar_manifest_inspect.py",
            "--arxml",
            str(FIXTURES / "sample.arxml"),
            "--manifest",
            str(FIXTURES / "sample_manifest.json"),
        )

        self.assertIn("SpeedIf", report["issues"]["duplicate_short_names"])
        self.assertIn("/Pkg/MissingIf", report["issues"]["unresolved_references"])
        self.assertEqual(report["summary"]["manifest_executables"], 1)

    def test_odx_inspect_reports_diagnostic_metadata_and_pdx_archives(self) -> None:
        report = run_json("odx_inspect.py", "--odx", str(FIXTURES / "sample.odx"))

        self.assertEqual(report["summary"]["documents"], 1)
        self.assertEqual(report["summary"]["services"], 1)
        self.assertEqual(report["summary"]["dids"], 1)
        self.assertEqual(report["summary"]["dtcs"], 1)
        self.assertIn("MissingReferencedObject", report["documents"][0]["issues"]["unresolved_references"])
        self.assertNotIn("did.vin", report["documents"][0]["issues"]["unresolved_references"])

        with tempfile.TemporaryDirectory() as temp_dir:
            pdx = Path(temp_dir) / "sample.pdx"
            with zipfile.ZipFile(pdx, "w") as archive:
                archive.write(FIXTURES / "sample.odx", "diag/sample.odx-d")
            pdx_report = run_json("odx_inspect.py", "--odx", str(pdx))
            self.assertEqual(pdx_report["summary"]["documents"], 1)

    def test_requirements_safety_tara_and_uds_sequence_scripts(self) -> None:
        req_report = run_json(
            "requirements_trace_lint.py",
            "--requirements",
            str(FIXTURES / "sample_requirements.md"),
            "--tests",
            str(FIXTURES / "sample_tests.csv"),
        )
        self.assertIn("REQ-002", req_report["issues"]["missing_verification_method"])
        self.assertEqual(req_report["issues"]["orphan_tests"][0]["test_id"], "TC-002")
        self.assertIn("REQ-003", req_report["issues"]["requirements_without_tests"])

        safety_template = run_json("safety_workproduct.py", "template", "--kind", "hara", "--item", "Brake Control")
        self.assertEqual(safety_template["status"], "draft_not_certification_evidence")
        safety_lint = run_json("safety_workproduct.py", "lint", "--kind", "hara", "--input", str(FIXTURES / "sample_hara.csv"))
        self.assertIn("H-002", safety_lint["issues"]["high_risk_rows_without_action"])

        tara_template = run_json("tara_workproduct.py", "template", "--kind", "threat-scenario", "--asset", "Diagnostic Service")
        self.assertEqual(tara_template["status"], "draft_not_cybersecurity_case_evidence")
        tara_lint = run_json("tara_workproduct.py", "lint", "--kind", "threat-scenario", "--input", str(FIXTURES / "sample_tara.csv"))
        self.assertIn("T-001", tara_lint["issues"]["high_risk_rows_without_treatment"])

        uds_lint = run_json(
            "uds_sequence_lint.py",
            "--sequence",
            str(FIXTURES / "sample_uds_sequence.csv"),
            "--odx",
            str(FIXTURES / "sample.odx"),
        )
        self.assertEqual(uds_lint["summary"]["steps"], 5)
        self.assertTrue(uds_lint["issues"]["risky_steps_without_preconditions"])
        self.assertEqual(uds_lint["issues"]["odx_risky_routines"][0]["routine_name"], "EraseMemory")

    def test_autosar_calibration_daq_triage_evidence_and_tool_scripts(self) -> None:
        autosar_report = run_json(
            "autosar_architecture_report.py",
            "--arxml",
            str(FIXTURES / "sample.arxml"),
            "--manifest",
            str(FIXTURES / "sample_manifest.json"),
        )
        self.assertEqual(autosar_report["summary"]["components"], 2)
        self.assertEqual(autosar_report["summary"]["ports"], 2)
        self.assertIn("/Pkg/MissingIf", autosar_report["issues"]["unresolved_references"])

        cal_report = run_json(
            "calibration_diff.py",
            "--base",
            str(FIXTURES / "cal_base.json"),
            "--candidate",
            str(FIXTURES / "cal_candidate.json"),
        )
        self.assertEqual(cal_report["summary"]["changed"], 1)
        self.assertIn("BoostLimit", cal_report["changes"]["removed"])

        daq_report = run_json(
            "xcp_daq_plan.py",
            "--a2l",
            str(FIXTURES / "sample.a2l"),
            "--lab",
            str(FIXTURES / "sample.lab"),
            "--max-signals-per-list",
            "1",
        )
        self.assertEqual(daq_report["summary"]["planned_measurements"], 2)
        self.assertEqual(daq_report["summary"]["daq_lists"], 2)
        hints = {item["name"]: item["kind"] for item in daq_report["plan"]["missing_symbol_hints"]}
        self.assertEqual(hints["IdleSpeedTarget"], "CHARACTERISTIC")
        self.assertEqual(hints["MissingSignal"], "absent")

        triage = run_json(
            "automotive_triage.py",
            "--inputs",
            str(FIXTURES / "sample.dbc"),
            str(FIXTURES / "sample_trace.log"),
            str(FIXTURES / "sample.a2l"),
            str(FIXTURES / "sample.odx"),
            str(FIXTURES / "sample.arxml"),
            str(FIXTURES / "sample_requirements.md"),
            "--bitrate",
            "500000",
        )
        self.assertGreaterEqual(triage["summary"]["analyzers_run"], 6)
        self.assertEqual(triage["summary"]["errors"], 0)

        evidence = run_json(
            "evidence_pack.py",
            "--inputs",
            str(FIXTURES / "sample.dbc"),
            str(FIXTURES / "sample_trace.log"),
            "--classification",
            "offline",
            "--assumption",
            "fixture evidence",
        )
        self.assertEqual(evidence["summary"]["artifacts"], 2)
        self.assertEqual(len(evidence["artifacts"][0]["sha256"]), 64)

        inventory = run_json("tool_inventory.py")
        self.assertIn("tools_checked", inventory["summary"])
        comparison = run_json("tool_compare.py", "--category", "can")
        self.assertEqual(comparison["summary"]["categories"], 1)

    def test_inspect_ehb_lists_filters_and_structured_symbol_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ehb = Path(temp_dir) / "sample.ehb"
            with zipfile.ZipFile(ehb, "w") as archive:
                archive.writestr(
                    "documentation/powertrain/signals.dita",
                    """
                    <topic>
                      <longname>Engine speed signal</longname>
                      <mode>measurement</mode>
                      <access>read</access>
                      <entry>Crankshaft speed used by the engine controller.</entry>
                      EngineSpeed
                    </topic>
                    """,
                )
                archive.writestr("documentation/body/body.dita", "DoorStatus")
                archive.writestr("images/overview.svg", "<svg/>")

            listed = run_json(
                "inspect_ehb.py",
                "--ehb",
                str(ehb),
                "--list-entries",
                "--limit",
                "1",
                "--module",
                "powertrain",
                "--entry-type",
                "dita",
            )
            self.assertEqual(len(listed["entries"]), 1)
            self.assertEqual(listed["entries"][0]["module"], "powertrain")
            self.assertEqual(listed["entries"][0]["entry_type"], "dita")

            report = run_json(
                "inspect_ehb.py",
                "--ehb",
                str(ehb),
                "--symbol",
                "EngineSpeed",
                "--module",
                "powertrain",
                "--entry-type",
                "dita",
            )
            self.assertEqual(report["match_counts_by_file"][str(ehb)], 1)
            self.assertEqual(report["matches"][0]["longname"], "Engine speed signal")
            self.assertEqual(report["matches"][0]["mode"], "measurement")
            self.assertEqual(report["matches"][0]["access"], "read")

    def test_scripts_reject_non_regular_inputs_and_malformed_structured_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fifo = Path(temp_dir) / "trace_fifo"
            os.mkfifo(fifo)
            non_regular = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "can_trace_summarize.py"),
                    "--trace",
                    str(fifo),
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(non_regular.returncode, 0)
            self.assertIn("regular file", non_regular.stderr)

            bad_arxml = Path(temp_dir) / "bad.arxml"
            bad_arxml.write_text("<AUTOSAR>", encoding="utf-8")
            bad_xml = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "autosar_manifest_inspect.py"),
                    "--arxml",
                    str(bad_arxml),
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(bad_xml.returncode, 0)
            self.assertIn("Invalid ARXML XML", bad_xml.stderr)

            bad_manifest = Path(temp_dir) / "bad.json"
            bad_manifest.write_text("{bad", encoding="utf-8")
            bad_json = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "autosar_manifest_inspect.py"),
                    "--arxml",
                    str(FIXTURES / "sample.arxml"),
                    "--manifest",
                    str(bad_manifest),
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(bad_json.returncode, 0)
            self.assertIn("Invalid manifest JSON", bad_json.stderr)

            bad_table = Path(temp_dir) / "bad_table.json"
            bad_table.write_text("{bad", encoding="utf-8")
            malformed_commands = [
                (
                    "calibration_diff.py",
                    ["--base", str(bad_table), "--candidate", str(FIXTURES / "cal_candidate.json")],
                    "Invalid calibration JSON",
                ),
                (
                    "requirements_trace_lint.py",
                    ["--requirements", str(bad_table)],
                    "Invalid requirements JSON",
                ),
                (
                    "safety_workproduct.py",
                    ["lint", "--kind", "hara", "--input", str(bad_table)],
                    "Invalid safety JSON",
                ),
                (
                    "tara_workproduct.py",
                    ["lint", "--kind", "threat-scenario", "--input", str(bad_table)],
                    "Invalid TARA JSON",
                ),
                (
                    "uds_sequence_lint.py",
                    ["--sequence", str(bad_table)],
                    "Invalid UDS sequence JSON",
                ),
            ]
            for script, args, expected in malformed_commands:
                completed = subprocess.run(
                    [sys.executable, str(SCRIPTS / script), *args, "--format", "json"],
                    cwd=ROOT,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertNotEqual(completed.returncode, 0, script)
                self.assertIn(expected, completed.stderr)

    def test_automotive_scripts_do_not_embed_live_transport_actions(self) -> None:
        unsafe_terms = (
            "import socket",
            "from socket",
            "import requests",
            "from requests",
            "import urllib",
            "from urllib",
            "import subprocess",
            "from subprocess",
            "import serial",
            "from serial",
            "/dev/",
            "ip link",
        )
        for path in sorted(SCRIPTS.glob("*.py")):
            lowered = path.read_text(encoding="utf-8").lower()
            for term in unsafe_terms:
                self.assertNotIn(term, lowered, f"{term} found in {path.name}")

        inventory_text = (SCRIPTS / "tool_inventory.py").read_text(encoding="utf-8")
        self.assertIn("Read-only inventory", inventory_text)


if __name__ == "__main__":
    unittest.main()
