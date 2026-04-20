import re

file_path = "kaggle-agi-benchmark/evaluator_kbench.py"

with open(file_path, "r") as f:
    content = f.read()

# Pattern to find tasks
# @kbench.task(name="...")
# def task_name():
#     """..."""
#     prompt = """..."""
#     return prompt, "X"


def transform_task(match):
    task_header = match.group(1)
    task_func = match.group(2)
    docstring = match.group(3)
    prompt_content = match.group(4)
    answer = match.group(5)

    new_task = f'{task_header}\ndef {task_func}(llm) -> bool:\n    {docstring}\n    prompt = """{prompt_content}"""\n    response = llm.prompt(prompt)\n    return kbench.assertions.assert_contains(response, "{answer}", expectation="Correct answer is {answer}")\n'
    return new_task


# Regex explanation:
# (@kbench\.task\(name="[^"]+"\))  -> Group 1: Decorator
# \ndef\s+([a-zA-Z0-9_]+)\(\):    -> Group 2: Function name
# \n\s+(""".*?""")                -> Group 3: Docstring
# \n\s+prompt\s+=\s+"""(.*?)"""   -> Group 4: Prompt content (non-greedy)
# \n\s+return\s+prompt,\s+"([^"]+)" -> Group 5: Answer
pattern = r'(@kbench\.task\(name="[^"]+"\))\ndef\s+([a-zA-Z0-9_]+)\(\):\n\s+(""".*?""")\n\s+prompt\s+=\s+"""(.*?)"""\n\s+return\s+prompt,\s+"([^"]+)"'

new_content = re.sub(pattern, transform_task, content, flags=re.DOTALL)

# Also fix the overall task
overall_task_pattern = r'@kbench\.task\(name="agi_cognitive_framework_overall"\)\ndef agi_cognitive_framework_overall\(\) -> float:.*?return float\(passed / total\) if total > 0 else 0\.0'
overall_replacement = """@kbench.task(name="agi_cognitive_framework_overall")
def agi_cognitive_framework_overall(llm) -> float:
    \"\"\"Overall benchmark score across all 5 cognitive tracks.\"\"\"
    tasks = [
        learning_synthetic_biology_01, learning_alien_grammar_02, learning_symbolic_logic_03,
        learning_grid_transformation_04, learning_temporal_rules_05, learning_arithmetic_base_06,
        learning_pattern_completion_07, learning_state_machine_08, learning_arbitrary_association_10,
        learning_cross_modal_proxy_11, learning_geometric_transform_10, learning_markov_process_11,
        learning_abstract_algebra_12, learning_causal_reasoning_13, learning_function_approx_14,
        learning_category_theory_15,
        metacognition_insufficient_info_01, metacognition_hidden_assumptions_02, metacognition_missing_parameters_03,
        metacognition_ambiguous_scope_04, metacognition_temporal_ambiguity_05, metacognition_statistical_power_06,
        metacognition_correlation_causation_07, metacognition_sampling_bias_08, metacognition_measurement_error_09,
        metacognition_counterfactual_10, metacognition_base_rate_11, metacognition_selection_bias_12,
        metacognition_missing_context_13, metacognition_vague_quantifiers_14, metacognition_unknown_variables_15,
        attention_irrelevant_info_01, attention_embedded_fact_02, attention_red_herring_03,
        attention_jargon_noise_04, attention_visual_search_05, attention_story_problem_06,
        attention_logical_noise_07, attention_format_distraction_08, attention_nested_statements_09,
        attention_temporal_attention_10, attention_quantity_tracking_11, attention_name_recognition_12,
        attention_pattern_interruption_13, attention_contradiction_detection_14, attention_critical_detail_15,
        exec_planning_simple_01, exec_resource_constraints_02, exec_dynamic_constraints_03,
        exec_multi_step_04, exec_deadline_scheduling_05, exec_inhibition_control_06,
        exec_task_switching_07, exec_working_memory_08, exec_cognitive_flexibility_09,
        exec_prioritization_10, exec_maze_navigation_11, exec_problem_reformulation_12,
        exec_error_monitoring_13, exec_time_management_14, exec_goal_hierarchy_15,
        social_false_belief_01, social_knowledge_asymmetry_02, social_intention_inference_03,
        social_deception_recognition_04, social_emotion_recognition_05, social_perspective_taking_06,
        social_communication_repair_07, social_cooperation_08, social_norm_violation_09,
        social_irony_sarcasm_10, social_reciprocity_11, social_group_dynamics_12,
        social_attribution_13, social_moral_reasoning_14, social_empathy_15
    ]
    
    passed = 0
    for task in tasks:
        try:
            if task.run(llm):
                passed += 1
        except Exception as e:
            print(f"Error running task {task}: {e}")
            
    return float(passed / len(tasks)) if tasks else 0.0"""

new_content = re.sub(overall_task_pattern, overall_replacement, new_content, flags=re.DOTALL)

with open(file_path, "w") as f:
    f.write(new_content)

print("Successfully transformed tasks in evaluator_kbench.py")
