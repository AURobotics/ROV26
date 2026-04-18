from pathlib import Path
import platform
import threading
import requests
import zipfile
import os


class Downloader:
    def __init__(
        self, url: str, destination: os.PathLike | str, headers: dict | None = None
    ):
        self.url = url
        self.destination = destination
        self.headers = headers
        self._stop_event = threading.Event()
        self.progress_percent: float = 0.0
        h_resp = requests.head(url, timeout=5)
        self.total_size = int(h_resp.headers.get("content-length", 0))
        self.status_message = "Downloader ready"

    def cancel(self):
        self._stop_event.set()

    def run(self):
        self.status_message = "Starting download"
        try:
            response = requests.get(
                self.url, stream=True, timeout=10, headers=self.headers
            )
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


class Extracter:
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


def get_stmprogrammer_url() -> str:
    resp = requests.get("https://developer.st.com/bundles/BundleRepositoryIndex.json")
    if resp.status_code == requests.status_codes.codes["ok"]:
        try:
            idx: dict = resp.json()
        except requests.JSONDecodeError:
            raise ConnectionError(
                "Invalid response received when obtaining STM Cube bundle index"
            )
    else:
        raise ConnectionError("Could not reach STM Cube bundle index")
    current_platform = platform.machine() + "-" + platform.system().lower()
    bundles: list[dict] = idx["bundles"]
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
        raise ValueError(
            "Programmer bundle was not found for current platform in the bundle index"
        )
    link = "https://developer.st.com/bundles/" + latest["path"]
    return link


def get_vhusbclient_url() -> str:
    system = platform.system()
    arch = platform.machine()
    match system:
        case "Darwin":
            return "https://www.virtualhere.com/sites/default/files/usbclient/VirtualHereUniversal.dmg"
        case "Linux":
            if arch in ["x86_64", "amd64"]:
                return (
                    "https://www.virtualhere.com/sites/default/files/usbclient/vhuit64"
                )
            elif arch == "aarch64":
                return "https://www.virtualhere.com/sites/default/files/usbclient/vhuitarm64"
        case "Windows":
            if arch in ["x86_64", "amd64"]:
                return "https://www.virtualhere.com/sites/default/files/usbclient/vhui64.exe"
            elif arch == "arm64":
                return "https://www.virtualhere.com/sites/default/files/usbclient/vhuiarm64.exe"

    raise ValueError(f"VHUSB Client was not found for your current platform")


def get_crab_detection_model_url(auth_token: str | None = None) -> str: ...
