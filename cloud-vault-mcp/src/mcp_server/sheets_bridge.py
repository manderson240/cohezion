"""Google Sheets bridge for reading and writing to Cohezion_Research sheet."""

import json
import logging
import subprocess
import urllib.parse
import urllib.request


logger = logging.getLogger(__name__)


class SheetsBridge:
    """Bridge to Google Sheets API using Application Default Credentials."""

    def __init__(
        self,
        spreadsheet_id: str = "1YcZObTni5L-VnA7O7TIl5ghoy-i3NfXuheFt_oFbmnk",
        quota_project: str = "cohezion-477604",
        sheet_name: str = "Sheet1",
    ):
        self._spreadsheet_id = spreadsheet_id
        self._quota_project = quota_project
        self._sheet_name = sheet_name

    def _get_token(self) -> str:
        """Get ADC access token via gcloud."""
        result = subprocess.run(
            ["gcloud", "auth", "application-default", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get ADC token: {result.stderr.strip()}")
        return result.stdout.strip()

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-goog-user-project": self._quota_project,
        }

    def _api_url(self, path: str) -> str:
        return (
            f"https://sheets.googleapis.com/v4/spreadsheets/"
            f"{self._spreadsheet_id}{path}"
        )

    def read_range(self, range_spec: str) -> list[list[str]]:
        """Read a range from the sheet.

        Args:
            range_spec: A1 notation range (e.g. 'A1:F100')

        Returns:
            List of rows, each a list of cell values.
        """
        token = self._get_token()
        full_range = f"{self._sheet_name}!{range_spec}"
        url = self._api_url(f"/values/{urllib.parse.quote(full_range)}")

        req = urllib.request.Request(url, headers=self._headers(token))
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return data.get("values", [])

    def read_column(self, column: str, start_row: int = 1) -> list[str]:
        """Read a single column.

        Args:
            column: Column letter (e.g. 'A', 'F')
            start_row: Starting row number (1-based)

        Returns:
            List of cell values.
        """
        rows = self.read_range(f"{column}{start_row}:{column}1000")
        return [r[0] if r else "" for r in rows]

    def update_row(
        self,
        row_num: int,
        status: str,
        abstractions: str,
        domain: str,
        integration_point: str,
    ) -> dict:
        """Update columns B-E for a row.

        Args:
            row_num: Row number (1-based, row 2 = first data row)
            status: Research status
            abstractions: Key abstractions
            domain: Domain category
            integration_point: Cohezion integration point
        """
        token = self._get_token()
        range_ = f"{self._sheet_name}!B{row_num}:E{row_num}"
        url = self._api_url(
            f"/values/{urllib.parse.quote(range_)}?valueInputOption=USER_ENTERED"
        )
        body = json.dumps(
            {
                "range": range_,
                "values": [[status, abstractions, domain, integration_point]],
            }
        ).encode()

        req = urllib.request.Request(
            url, data=body, headers=self._headers(token), method="PUT"
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def batch_update(self, data: list[dict]) -> dict:
        """Batch update multiple ranges.

        Args:
            data: List of {"range": "Sheet1!B2:E2", "values": [["val1", ...]]} dicts

        Returns:
            API response dict.
        """
        token = self._get_token()
        url = self._api_url("/values:batchUpdate")
        payload = json.dumps({"valueInputOption": "RAW", "data": data}).encode()

        req = urllib.request.Request(
            url, data=payload, headers=self._headers(token), method="POST"
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def update_vault_note_column(self, row_num: int, vault_note: str) -> dict:
        """Update column F (Vault Note) for a row.

        Args:
            row_num: Row number (1-based)
            vault_note: Vault note filename
        """
        token = self._get_token()
        range_ = f"{self._sheet_name}!F{row_num}"
        url = self._api_url(
            f"/values/{urllib.parse.quote(range_)}?valueInputOption=USER_ENTERED"
        )
        body = json.dumps({"range": range_, "values": [[vault_note]]}).encode()

        req = urllib.request.Request(
            url, data=body, headers=self._headers(token), method="PUT"
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def get_all_rows(self) -> list[dict]:
        """Read all data rows as dicts.

        Returns:
            List of dicts with keys: row, link, status, abstractions, domain,
            integration_point, vault_note
        """
        rows = self.read_range("A1:F1000")
        if len(rows) < 2:
            return []

        result = []
        for i, row in enumerate(rows[1:], start=2):
            # Pad row to 6 columns
            padded = row + [""] * (6 - len(row))
            result.append(
                {
                    "row": i,
                    "link": padded[0],
                    "status": padded[1],
                    "abstractions": padded[2],
                    "domain": padded[3],
                    "integration_point": padded[4],
                    "vault_note": padded[5],
                }
            )
        return result
