import typer

from pephubclient import __app_name__, __version__

from pephubclient.helpers import MessageHandler
from pephubclient.pephubclient import PEPHubClient
from pephubclient.helpers import call_client_func

_client = PEPHubClient()

app = typer.Typer()


@app.command()
def login():
    """
    Login to PEPhub
    """
    call_client_func(
        _client.login
    )


@app.command()
def logout():
    """
    Logout
    """
    _client.logout()


@app.command()
def pull(
    project_registry_path: str,
    force: bool = typer.Option(False, help="Overwrite project if it exists."),
):
    """
    Download and save project locally.
    """
    call_client_func(
        _client.pull,
        project_registry_path=project_registry_path,
        force=force,
    )


@app.command()
def push(
    cfg: str = typer.Argument(
        ...,
        help="Project config file (YAML) or sample table (CSV/TSV)"
        "with one row per sample to constitute project",
    ),
    namespace: str = typer.Option(..., help="Project namespace"),
    name: str = typer.Option(..., help="Project name"),
    tag: str = typer.Option(None, help="Project tag"),
    force: bool = typer.Option(
        False, help="Force push to the database. Use it to update, or upload project."
    ),
    is_private: bool = typer.Option(False, help="Upload project as private."),
):
    """
    Upload/update project in PEPhub
    """

    call_client_func(
        _client.push,
        cfg=cfg,
        namespace=namespace,
        name=name,
        tag=tag,
        is_private=is_private,
        force=force,
    )



@app.command()
def version():
    """
    Package version
    """
    print(f"{__app_name__} v{__version__}")
