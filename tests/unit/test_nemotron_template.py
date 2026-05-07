"""V-model test: verify all 9 required markers in Nemotron v5 training template."""


def test_v5_template_markers():
    """V-model test: verify all 9 required markers in Nemotron training template."""
    from cohezion.integrations.kaggle_training_improved import KaggleTrainingManager

    tmpl = KaggleTrainingManager().get_training_script_template()
    required = [
        "all-linear",
        "DataCollatorForSeq2Seq",
        "label_pad_token_id=-100",
        "dtype=torch.bfloat16",       # was torch_dtype=; template uses dtype= kwarg form
        "lora_alpha=64",
        r"\boxed{",                    # was BOXED_INSTRUCTION; template uses LaTeX \boxed{} notation
        "adapter_config.json",
        "enable_input_require_grads",
        "EVAL_SUFFIX",                 # was extract_boxed; template defines EVAL_SUFFIX constant
    ]
    missing = [m for m in required if m not in tmpl]
    assert not missing, f"Template missing markers: {missing}"
