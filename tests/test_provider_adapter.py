import pytest

from rongwei_plugin.adapters.openai_compatible import (
    PROVIDERS,
    ProviderConfigurationError,
    get_provider_config,
)


def test_selected_chinese_providers_are_registered():
    assert set(PROVIDERS) == {"deepseek", "qwen", "doubao", "glm", "qianfan"}


@pytest.mark.parametrize(
    ("provider", "key_env", "model_env", "base_env", "expected_base"),
    [
        ("deepseek", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        ("qwen", "DASHSCOPE_API_KEY", "QWEN_MODEL", "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ("doubao", "ARK_API_KEY", "DOUBAO_MODEL", "ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        ("glm", "DASHSCOPE_API_KEY", "GLM_MODEL", "GLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ("qianfan", "QIANFAN_API_KEY", "QIANFAN_MODEL", "QIANFAN_BASE_URL", "https://qianfan.baidubce.com/v2"),
    ],
)
def test_provider_config_uses_expected_environment_variables(
    monkeypatch, provider, key_env, model_env, base_env, expected_base
):
    monkeypatch.setenv(key_env, "test-api-key")
    monkeypatch.setenv(model_env, "test-model")
    monkeypatch.delenv(base_env, raising=False)

    spec, api_key, model, base_url = get_provider_config(provider)
    assert api_key == "test-api-key"
    assert model == "test-model"
    assert base_url == expected_base
    assert spec.base_url_env == base_env


def test_deepseek_and_glm_have_provider_specific_tool_parameters(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret-deepseek")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-model")
    deepseek, *_ = get_provider_config("deepseek")
    assert deepseek.thinking_mode is True

    monkeypatch.setenv("DASHSCOPE_API_KEY", "secret-dashscope")
    monkeypatch.setenv("GLM_MODEL", "glm-model")
    glm, *_ = get_provider_config("glm")
    assert glm.thinking_mode is False
    assert glm.extra_body == {"tool_stream": True}


def test_missing_credentials_do_not_expose_secret_values(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_MODEL", raising=False)
    with pytest.raises(ProviderConfigurationError) as exc:
        get_provider_config("deepseek")
    message = str(exc.value)
    assert "DEEPSEEK_API_KEY" in message
    assert "DEEPSEEK_MODEL" in message
    assert "secret" not in message


def test_unknown_provider_is_rejected():
    with pytest.raises(ProviderConfigurationError):
        get_provider_config("some-global-model")
