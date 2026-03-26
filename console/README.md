# ROV26/console

## Development Dependencies

### uv: project management
Make sure you install uv [\[official instructions\]](https://docs.astral.sh/uv/getting-started/installation/):

Windows:
```ps1
winget install --id astral-sh.uv
```

Linux/ MacOS:
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```
or
```sh
wget -qO- https://astral.sh/uv/install.sh | sh
```

### Github CLI

If your platform has supported `opencv-python` wheels released under [releases](https://github.com/AURobotics/ROV26/releases), do not skip this step.

Windows:
```ps1
winget install --id GitHub.cli
```

**Make sure to restart your shell or IDE to refresh any PATH updates**

## Python dependencies

Due to how we handle `opencv-python` and `gstreamer` support, during the initial venv setup, you should follow the steps corresponding to your platform:

### Windows

```ps1
.\scripts\setup_venv.ps1
```

**If the repository is private** you must login with Github CLI at least once before running the setup_venv script
```sh
gh auth login
```

This gets opencv builds from the [releases](https://github.com/AURobotics/ROV26/releases)

## Linux
You must download `opencv-python` from your distribution's package repository along with the needed `gstreamer` plugins.

The recommended workflow is setting up an `ubuntu:latest` container and installing the following packages:
```sh
apt install -y curl vim gcc g++ build-essential git \
python3-opencv gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-vaapi  gstreamer1.0-tools libgstreamer1.0-dev
```

For `distrobox` users, here is an example of a good container setup for this project:
```sh
distrobox-create --image ubuntu:latest -n CUSTOM_NAME --home CUSTOM_HOME --additional-flags "--env VIRTUALIZED_UDEV=1 --group-add keep-groups --device /dev/input"
```
you can optionally append `--nvidia` to the very end of the command for Nvidia GPU support

After setting up the system, you must run:
```sh
./scripts/setup_venv.sh
```

## IDE Setup

Remember to choose your `.venv`'s interpreter or choose `uv` as the virtual environment manager in your IDE.

### Visual Studio Code (recommended)
You will find recommended extensions and settings under loaded into your IDE if [.vscode](./.vscode/) is loaded (automatically by opening this specific project's folder).
