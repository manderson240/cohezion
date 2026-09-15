
from cohezion.security.secret_scrubber import (
    auto_heal_scrub_file,
    contains_unredacted_credentials,
    scrub_text,
    verify_command_safety,
)


def test_scrub_google_oauth_tokens():
    # Build fixture tokens programmatically so this file never contains a
    # literal matching the scrubber's (or GitHub Push Protection's) patterns.
    tail = "x" * 120
    access = "ya29." + tail
    refresh = "1//" + "A" * 60
    raw = (
        'token = {"access_token":"' + access + '",'
        '"token_type":"Bearer",'
        '"refresh_token":"' + refresh + '",'
        '"expiry":"2026-09-07T01:06:56.377449378-04:00"}'
    )
    assert "ya29." in raw and "1//" in raw
    assert contains_unredacted_credentials(raw)

    scrubbed = scrub_text(raw)
    assert "ya29." not in scrubbed
    assert "1//" not in scrubbed
    assert "[REDACTED:GOOGLE_ACCESS_TOKEN]" in scrubbed or "[REDACTED:ACCESS_TOKEN]" in scrubbed
    assert "[REDACTED:GOOGLE_REFRESH_TOKEN]" in scrubbed or "[REDACTED:REFRESH_TOKEN]" in scrubbed


def test_scrub_api_keys_and_bearer():
    text = "Authorization: Bearer sk-ant-api03-abcdef1234567890abcdef1234567890 and ghp_123456789012345678901234567890123456"
    scrubbed = scrub_text(text)
    assert "sk-ant" not in scrubbed
    assert "ghp_" not in scrubbed
    assert "[REDACTED" in scrubbed


def test_scrub_kaggle_and_bluequbit_credentials():
    # Programmatic dummy tokens (no real secrets)
    dummy_hex = "a" * 32
    kaggle_json = '{"username": "testuser", "key": "' + dummy_hex + '"}'
    scrubbed = scrub_text(kaggle_json)
    assert dummy_hex not in scrubbed
    assert "[REDACTED:KAGGLE_KEY]" in scrubbed

    bq_token = "BQUBIT_" + "b" * 30
    bq_env = "BLUEQUBIT_API_TOKEN=" + bq_token
    scrubbed_bq = scrub_text(bq_env)
    assert bq_token not in scrubbed_bq
    assert "[REDACTED:BLUEQUBIT_TOKEN]" in scrubbed_bq


def test_verify_command_safety_blocking():
    # Attempting to read rclone.conf
    v1 = verify_command_safety("cat ~/.config/rclone/rclone.conf | grep token")
    assert not v1.allowed
    assert "rclone" in v1.violation_reason
    assert "rclone listremotes" in v1.suggested_alternative

    # Attempting to grep .env
    v2 = verify_command_safety("grep -i secret .env")
    assert not v2.allowed
    assert ".env" in v2.violation_reason

    # Attempting to cat kaggle.json
    v_kg = verify_command_safety("cat ~/.kaggle/kaggle.json")
    assert not v_kg.allowed
    assert "kaggle" in v_kg.violation_reason

    # Attempting to cat bluequbit credentials
    v_bq = verify_command_safety("cat bluequbit_credentials.json")
    assert not v_bq.allowed
    assert "bluequbit" in v_bq.violation_reason

    # Safe commands
    v3 = verify_command_safety("rclone listremotes")
    assert v3.allowed

    v4 = verify_command_safety("pytest tests/security/ -v")
    assert v4.allowed


def test_auto_heal_scrub_file(tmp_path):
    log_file = tmp_path / "leaked.log"
    log_file.write_text(
        "2026-09-07 [DEBUG] Loaded token ya29.sample_test_access_token_with_high_entropy_123456789\n"
        "2026-09-07 [INFO] System operational."
    )
    assert contains_unredacted_credentials(log_file.read_text())

    redacted_count = auto_heal_scrub_file(log_file)
    assert redacted_count == 1

    content_after = log_file.read_text()
    assert "ya29." not in content_after
    assert "[REDACTED:GOOGLE_ACCESS_TOKEN]" in content_after
    assert not contains_unredacted_credentials(content_after)
