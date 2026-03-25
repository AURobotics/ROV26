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
If the repository is private, Github CLI will be necessary for the next step.

Windows:
```ps1
winget install --id GitHub.cli
```

Linux:
Follow your [distro-specific instructions](https://github.com/cli/cli/blob/trunk/docs/install_linux.md)


**Make sure to restart your shell or IDE to refresh any PATH updates**

## Python dependencies
At any time, you may run the following command to pull in the dependencies.
```sh
uv sync
```

If custom wheels aren't being resolved properly, you may need to do a cleanup before running the previous command.

Windows:
```ps1
Remove-Item -Recurse -Force .venv
Remove-Item uv.lock
```

Linux/ MacOS:
```sh
rm -rf .venv uv.lock
```

Then run
```sh
uv sync --no-cache
```


### opencv-python builds with GStreamer support

To get the opencv builds from the [releases](https://github.com/AURobotics/ROV26/releases), simply run:

Windows:
```ps1
./scripts/get_opencv.ps1
```

Linux:
```sh
./scripts/get_opencv.sh
```

### If the repository is private
You must login with Github CLI at least once before running the get_opencv script
```sh
gh auth login
```
