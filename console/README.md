# ROV26/console

## Development Dependencies

### Pixi: project management
Make sure you install Pixi [\[official instructions\]](https://pixi.prefix.dev/latest/installation/):

Windows:
```ps1
winget install prefix-dev.pixi
```

Linux/ MacOS:
```sh
curl -fsSL https://pixi.sh/install.sh | sh
```
or
```sh
wget -qO- https://pixi.sh/install.sh | sh
```


**Make sure to restart your shell or IDE to refresh any PATH updates**

For `distrobox` users, here is an example of a good container setup for this project:
```sh
distrobox-create --image ubuntu:latest -n CUSTOM_NAME --home CUSTOM_HOME --additional-flags "--env VIRTUALIZED_UDEV=1 --group-add keep-groups --device /dev/input"
```
you can optionally append `--nvidia` to the very end of the command for Nvidia GPU support


## IDE Setup

Remember to choose your `.pixi/`'s interpreter or choose `pixi` as the virtual environment manager in your IDE.

### Visual Studio Code (recommended)
You will find recommended extensions and settings loaded into your IDE if [.vscode](./.vscode/) is loaded (automatically by opening this specific project's folder).
