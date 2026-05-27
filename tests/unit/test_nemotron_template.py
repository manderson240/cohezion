"""V-model test: verify all 9 required markers in Nemotron v5 training template."""


def test_v5_template_markers():
    """V-model test: verify all 9 required markers in Nemotron training template."""
    from cohezion.integrations.kaggle_training_improved import KaggleTrainingManager

    tmpl = KaggleTrainingManager().get_training_script_template()
    required = [
        "all-linear",
        "DataCollatorForSeq2Seq",
        "label_pad_token_id=-100",
        "dtype=torch.bfloat16",  # was torch_dtype=; template uses dtype= kwarg form
        "lora_alpha=64",
        "BOXED_INSTRUCTION",  # constant defined in template for boxed-answer prompt format
        "adapter_config.json",
        "enable_input_require_grads",
        "extract_boxed",  # function defined in template to parse \boxed{} output
    ]
    missing = [m for m in required if m not in tmpl]
    assert not missing, f"Template missing markers: {missing}"
