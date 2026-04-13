import os
from pathlib import Path
import threading
import requests
import platform
import zipfile


class ProgrammerDownloader:
    def __init__(self, url: str, destination: os.PathLike | str):
        self.url = url
        self.destination = destination
        self._stop_event = threading.Event()
        self.progress_percent: float = 0.0
        self.total_size: int = 0
        self.status_message = "Downloader ready"

    def fetch_bundle_index(self) -> dict:
        resp = requests.get(
            "https://developer.st.com/bundles/BundleRepositoryIndex.json"
        )
        if resp.status_code == requests.status_codes.codes["ok"]:
            try:
                return resp.json()
            except requests.JSONDecodeError:
                raise ConnectionError(
                    "Invalid response received when obtaining STM Cube bundle index"
                )
        raise ConnectionError("Could not reach STM Cube bundle index")

    def obtain_programmer_bundle(self) -> dict:
        current_platform = platform.machine() + "-" + platform.system().lower()
        bundles: list[dict] = self.fetch_bundle_index()["bundles"]
        try:
            programmer_bundles = list(
                filter(
                    lambda b: (
                        b["details"]["name"] == "programmer"
                        and b["details"]["platform"] == current_platform
                    ),
                    bundles,
                )
            )
            latest = sorted(
                programmer_bundles,
                key=lambda b: b["details"]["version"],
                reverse=True,
            )[0]
        except (KeyError, IndexError):
            raise ConnectionError(
                "Programmer bundle was not found for current platform in the bundle index"
            )
        return latest

    def cancel(self):
        self._stop_event.set()

    def run(self):
        self.status_message = "Starting download"
        try:
            programmer_bundle = self.obtain_programmer_bundle()
            link: str = "https://developer.st.com/bundles/" + programmer_bundle["path"]
            self.total_size = programmer_bundle["packed_size"]
            response = requests.get(link, stream=True, timeout=10)
            response.raise_for_status()
            downloaded = 0
            self.status_message = "Downloading"
            with open(self.destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._stop_event.is_set():
                        self.status_message = "Download cancelled by user"
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if self.total_size > 0:
                            self.progress = downloaded / self.total_size
            self.status_message = "Download finished"

        except Exception as ex:
            self.status_message = str(ex)


class ProgrammerExtracter:
    def __init__(self, source_path: os.PathLike | str, dest_path: os.PathLike | str):
        self.source = Path(source_path).resolve()
        self.dest = Path(dest_path).resolve()
        self.status_message = "Extracter ready"

    def run(self) -> None:
        self.status_message = "Extracting"
        try:
            with zipfile.ZipFile(self.source, "r") as zip_ref:
                zip_ref.extractall(self.dest)
            self.status_message = "Extraction finished"
        except Exception as ex:
            self.status_message = str(ex)
