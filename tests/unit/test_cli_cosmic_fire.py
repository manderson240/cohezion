from typer.testing import CliRunner

from cohezion.cli.main import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "CLI Version" in result.stdout
    assert "0.1.0" in result.stdout


def test_cli_hello():
    result = runner.invoke(app, ["hello"])
    assert result.exit_code == 0
    assert "Cohezion" in result.stdout


def test_cli_fire_status():
    result = runner.invoke(app, ["fire", "status"])
    assert result.exit_code == 0
    assert "Cosmic Fire Triune State" in result.stdout
    assert "Electric Fire" in result.stdout
    assert "Solar Fire" in result.stdout
    assert "Fire by Friction" in result.stdout


def test_cli_cosmic_alias_status():
    result = runner.invoke(app, ["cosmic", "status"])
    assert result.exit_code == 0
    assert "Seven Ray Swarm Dynamics" in result.stdout


def test_cli_fire_ignite():
    result = runner.invoke(app, ["fire", "ignite", "--coherence", "0.50"])
    assert result.exit_code == 0
    assert "Cosmic Fire Ignited Successfully" in result.stdout


def test_cli_fire_eval():
    result = runner.invoke(app, ["fire", "eval", "0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5"])
    assert result.exit_code == 0
    assert "12D Vector Evaluation" in result.stdout
    assert "Harmonic Equilibrium" in result.stdout


def test_cli_auto_status():
    result = runner.invoke(app, ["auto", "status"])
    assert result.exit_code == 0
    assert "Recursive Autopoiesis & Sovereign Tri-Silicon State" in result.stdout
    assert "Phoenix Architecture" in result.stdout


def test_cli_auto_phoenix():
    result = runner.invoke(app, ["auto", "phoenix"])
    assert result.exit_code == 0
    assert "The Deletion Test Passed" in result.stdout
    assert "Phoenix Architecture Rebirth" in result.stdout
