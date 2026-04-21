from abc import ABC, abstractmethod
from pathlib import Path
import platform
import shutil
import threading
import requests
import zipfile
from os import PathLike
import stat
from urllib.parse import quote

from console.env import pathing
from packaging import version


class Downloader:
    def __init__(
        self,
        url: str,
        destination: PathLike | str,
        headers: dict | None = None,
        total_size: int = 0,
    ):
        self.url = url
        self.destination = Path(destination)
        self.headers = headers
        self.stop_event = threading.Event()
        self.downloaded_bytes = 0
        self.total_size = total_size
        self.canceled = False
        self.done = False
        self.file_name = None

    def cancel(self):
        self.stop_event.set()

    def run(self):
        try:
            if self.total_size == 0:
                self.total_size = int(
                    requests.head(self.url, timeout=5).headers.get("content-length", 0)
                )
            response = requests.get(
                self.url, stream=True, timeout=10, headers=self.headers
            )
            response.raise_for_status()
            with open(self.destination, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.stop_event.is_set():
                        self.canceled = True
                        return
                    if chunk:
                        f.write(chunk)
                        self.downloaded_bytes += len(chunk)
            self.done = True
        except Exception:
            raise


class Extracter:
    def __init__(self, source_path: PathLike | str, dest_path: PathLike | str):
        self.source = Path(source_path).resolve()
        self.dest = Path(dest_path).resolve()
        self.file_count = 0
        self.extracted_file_count = 0
        self.current_file_name: str = ""
        self.done = False
        self.canceled = False
        self.stop_event = threading.Event()

    def cancel(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        try:
            with zipfile.ZipFile(self.source, "r") as z:
                files = z.namelist()
                self.file_count = len(files)
                for file in files:
                    if self.stop_event.is_set():
                        self.canceled = True
                        return
                    self.current_file_name = file
                    z.extract(file, self.dest)
                    self.extracted_file_count += 1
            self.done = True
        except:
            raise


class ThirdPartyDownloader(ABC):
    tempfile_lock = threading.Lock()
    tempfile_count = 0

    def __init__(
        self,
        destination: str | PathLike[str],
        extract: bool = False,
        request_headers: dict[str, str] | None = None,
        executables: list[str] = [],
    ) -> None:
        self._destination = Path(destination).resolve()
        self._extract = extract
        self._request_headers = request_headers
        self._dl_handle: Downloader | None = None
        self._extract_handle: Extracter | None = None
        self._exception: str | None = None
        self._progress = 0
        self._status = "Ready"
        self._executables = [self._destination / f for f in executables]
        temps = list(pathing.temp().glob("download_*")) + list(
            pathing.temp().glob("unzip_*")
        )
        if temps:
            ThirdPartyDownloader.tempfile_count = max(
                int(p.name.split("_")[-1]) for p in temps
            )
        self._canceled = threading.Event()

    @classmethod
    def next_file_idx(cls) -> int:
        with cls.tempfile_lock:
            cls.tempfile_count += 1
            return cls.tempfile_count

    @staticmethod
    @abstractmethod
    def _get_url_and_size() -> tuple[str, int]: ...

    @property
    def progress_percent(self) -> int:
        self._update_status()
        return self._progress

    @property
    def status_message(self) -> str:
        self._update_status()
        return self._status

    def _update_status(self) -> None:
        if self._exception:
            self._status = f"Failed to download: {self._exception}"
            self._progress = 100
            return
        if not self._dl_handle:
            self._status = "Ready"
            self._progress = 0
            return
        if self._dl_handle.canceled:
            self._status = "Canceled by user"
            self._progress = 100
            return
        if self._dl_handle.stop_event.is_set():
            self._status = "Stopping download.."
            self._progress = 100
            return
        if self._dl_handle.total_size == 0:
            self._status = "Fetching file"
            self._progress = 0
            return
        if self._dl_handle.downloaded_bytes == 0:
            self._status = "Starting download"
            self._progress = 0
            return
        if 0 < self._dl_handle.downloaded_bytes < self._dl_handle.total_size:
            self._status = "Downloading"
            self._progress = int(
                100 * self._dl_handle.downloaded_bytes / self._dl_handle.total_size
            )
            return
        if self._dl_handle.done and not self._extract_handle:
            self._status = "Downloaded"
            self._progress = 100
            return
        if not self._extract_handle:
            self._status = "Downloaded"
            self._progress = 100
            return
        if self._extract_handle.done:
            self._status = "Download succesful"
            self._progress = 100
            return
        if self._extract_handle.file_count == 0:
            self._status = "Starting extraction"
            self._progress = 0
            return
        if self._extract_handle.canceled:
            self._status = "Canceled by user"
            self._progress = 100
            return
        if self._extract_handle.stop_event.is_set():
            self._status = "Stopping extraction.."
            self._progress = 100
            return
        if (
            0
            < self._extract_handle.extracted_file_count
            < self._extract_handle.file_count
        ):
            self._status = f"Extracting ({self._extract_handle.extracted_file_count}/{self._extract_handle.file_count}): {self._extract_handle.current_file_name}"
            self._progress = int(
                100
                * self._extract_handle.extracted_file_count
                / self._extract_handle.file_count
            )
            return

    @property
    def destination(self) -> Path:
        return self._destination

    def cancel(self) -> None:
        if self._dl_handle and not self._dl_handle.done:
            self._dl_handle.cancel()
        elif self._extract_handle and not self._extract_handle.done:
            self._extract_handle.cancel()
        self._canceled.set()

    def run(self) -> None:
        dl_dest = pathing.temp() / f"download_{self.next_file_idx()}"
        extract_dest = pathing.temp() / f"unzip_{self.next_file_idx()}"
        try:
            req_data = self._get_url_and_size()
            self._dl_handle = Downloader(
                req_data[0], dl_dest, self._request_headers, req_data[1]
            )
            if self._canceled.is_set():
                return
            self._dl_handle.run()
            if not self._dl_handle.done:
                return
            if not self._extract:
                self._destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.move(dl_dest, self._destination)
                return
            extract_dest.mkdir(exist_ok=True)
            self._extract_handle = Extracter(dl_dest, extract_dest)
            if self._canceled.is_set():
                return
            self._extract_handle.run()
            if not self._extract_handle.done:
                return
            shutil.copytree(extract_dest, self._destination, dirs_exist_ok=True)
            for ex in self._executables:
                if ex.is_file():
                    ex.chmod(stat.S_IRWXO | stat.S_IRWXG | stat.S_IRWXU)

        except Exception as ex:
            print(f"[WARN] | {ex}")
            self._exception = ex.__class__.__name__
        finally:
            dl_dest.unlink(missing_ok=True)
            shutil.rmtree(extract_dest, ignore_errors=True)


class StmProgrammerDownloader(ThirdPartyDownloader):
    def __init__(self, destination: str | PathLike[str]) -> None:
        """A download state holder for the STM32_Programmer_CLI

        Args:
            destination (str | PathLike[str]): destination for the programmer executable
        """
        true_dest = Path(destination).parent.parent
        self._dest = Path(destination).resolve()
        super().__init__(
            true_dest, extract=True, executables=["bin/STM32_Programmer_CLI"]
        )

    @property
    def destination(self) -> Path:
        return self._dest

    @staticmethod
    def _get_url_and_size() -> tuple[str, int]:
        resp = requests.get(
            "https://developer.st.com/bundles/BundleRepositoryIndex.json"
        )
        if resp.status_code == requests.status_codes.codes["ok"]:
            try:
                idx: dict = resp.json()
            except requests.JSONDecodeError:
                raise ConnectionError(
                    "Invalid response received when obtaining STM Cube bundle index"
                )
        else:
            raise ConnectionError("Could not reach STM Cube bundle index")
        arch = platform.machine().lower()
        if arch == "amd64":
            arch = "x86_64"
        current_platform = arch + "-" + platform.system().lower()
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
            latest = max(
                programmer_bundles,
                key=lambda b: version.parse(b["details"]["version"]),
            )
        except (KeyError, IndexError):
            raise ValueError(
                "Programmer bundle was not found for current platform in the bundle index"
            )
        link = "https://developer.st.com/bundles/" + quote(latest["path"])
        size = latest["packed_size"]
        return (link, size)


class VirtualHereClientDownloader(ThirdPartyDownloader):
    def __init__(self, destination: str | PathLike[str]) -> None:
        super().__init__(destination)

    @staticmethod
    def _get_url_and_size() -> tuple[str, int]:
        system = platform.system().lower()
        arch = platform.machine().lower()
        match system:
            case "darwin":
                return (
                    "https://www.virtualhere.com/sites/default/files/usbclient/VirtualHereUniversal.dmg",
                    0,
                )
            case "linux":
                if arch in ["x86_64", "amd64"]:
                    return (
                        "https://www.virtualhere.com/sites/default/files/usbclient/vhuit64",
                        0,
                    )
                elif arch == "aarch64":
                    return (
                        "https://www.virtualhere.com/sites/default/files/usbclient/vhuitarm64",
                        0,
                    )
            case "windows":
                if arch in ["x86_64", "amd64"]:
                    return (
                        "https://www.virtualhere.com/sites/default/files/usbclient/vhui64.exe",
                        0,
                    )
                elif arch == "arm64":
                    return (
                        "https://www.virtualhere.com/sites/default/files/usbclient/vhuiarm64.exe",
                        0,
                    )

        raise ValueError(f"VHUSB Client was not found for your current platform")


class CrabDetectionModelDownloader(ThirdPartyDownloader):
    def __init__(self, destination: str | PathLike[str]) -> None:
        super().__init__(destination)

    @staticmethod
    def _get_url_and_size() -> tuple[str, int]:
        resp = requests.get(
            "https://api.github.com/repos/AURobotics/ROV26/releases"
        ).json()
        models = [
            release
            for release in resp
            if release["tag_name"].startswith("crab-counting")
        ]
        latest = max(
            models,
            key=lambda m: version.parse(m["tag_name"].split("@")[1]),
        )
        for asset in latest["assets"]:
            if asset["name"].endswith(".pt"):
                return (asset["browser_download_url"], asset["size"])
        raise ValueError("Could not find a released model file")
