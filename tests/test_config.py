from invoice_automation.config import load_config


def test_load_config_reads_yaml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "invoice:\n"
        "  year:\n"
        "  month: 5\n"
        "recipients:\n"
        "  sheet_id: abc123\n"
    )

    config = load_config(str(config_file))

    assert config["invoice"]["month"] == 5
    assert config["recipients"]["sheet_id"] == "abc123"
