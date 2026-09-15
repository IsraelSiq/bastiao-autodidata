from src.model import OmniRouteModel


def test_model_uses_configured_temperature(monkeypatch):
    monkeypatch.setenv("BASTIAO_TEMPERATURE", "0.05")
    model = OmniRouteModel()

    assert model.temperature == 0.05
