@kbench.task(name="agi_cognitive_framework_overall")
def agi_cognitive_framework_overall(llm) -> float:
    """Overall benchmark score across all 5 cognitive tracks."""
    tasks = [
        learning_synthetic_biology_01,
        learning_alien_grammar_02,
        learning_symbolic_logic_03,
        learning_grid_transformation_04,
        learning_temporal_rules_05,
        learning_arithmetic_base_06,
        learning_pattern_completion_07,
        learning_state_machine_08,
        learning_arbitrary_association_10,
        learning_cross_modal_proxy_11,
        learning_geometric_transform_10,
        learning_markov_process_11,
        learning_abstract_algebra_12,
        learning_causal_reasoning_13,
        learning_function_approx_14,
        learning_category_theory_15,
        metacognition_insufficient_info_01,
        metacognition_hidden_assumptions_02,
        metacognition_missing_parameters_03,
        metacognition_ambiguous_scope_04,
        metacognition_temporal_ambiguity_05,
        metacognition_statistical_power_06,
        metacognition_correlation_causation_07,
        metacognition_sampling_bias_08,
        metacognition_measurement_error_09,
        metacognition_counterfactual_10,
        metacognition_base_rate_11,
        metacognition_selection_bias_12,
        metacognition_missing_context_13,
        metacognition_vague_quantifiers_14,
        metacognition_unknown_variables_15,
        attention_irrelevant_info_01,
        attention_embedded_fact_02,
        attention_red_herring_03,
        attention_jargon_noise_04,
        attention_visual_search_05,
        attention_story_problem_06,
        attention_logical_noise_07,
        attention_format_distraction_08,
        attention_nested_statements_09,
        attention_temporal_attention_10,
        attention_quantity_tracking_11,
        attention_name_recognition_12,
        attention_pattern_interruption_13,
        attention_contradiction_detection_14,
        attention_critical_detail_15,
        exec_planning_simple_01,
        exec_resource_constraints_02,
        exec_dynamic_constraints_03,
        exec_multi_step_04,
        exec_deadline_scheduling_05,
        exec_inhibition_control_06,
        exec_task_switching_07,
        exec_working_memory_08,
        exec_cognitive_flexibility_09,
        exec_prioritization_10,
        exec_maze_navigation_11,
        exec_problem_reformulation_12,
        exec_error_monitoring_13,
        exec_time_management_14,
        exec_goal_hierarchy_15,
        social_false_belief_01,
        social_knowledge_asymmetry_02,
        social_intention_inference_03,
        social_deception_recognition_04,
        social_emotion_recognition_05,
        social_perspective_taking_06,
        social_communication_repair_07,
        social_cooperation_08,
        social_norm_violation_09,
        social_irony_sarcasm_10,
        social_reciprocity_11,
        social_group_dynamics_12,
        social_attribution_13,
        social_moral_reasoning_14,
        social_empathy_15,
    ]

    passed = 0
    for task in tasks:
        try:
            if task.run(llm):
                passed += 1
        except Exception as e:
            print(f"Error running task {task.name}: {e}")

    return float(passed / len(tasks)) if tasks else 0.0


if __name__ == "__main__":
    import requests

    class OllamaLLM:
        def __init__(self, model="phi4:latest"):
            self.model = model
            self.url = "http://localhost:11434/api/generate"

        def prompt(self, p):
            payload = {"model": self.model, "prompt": p, "stream": False}
            try:
                response = requests.post(self.url, json=payload, timeout=60.0)
                if response.status_code == 200:
                    return response.json().get("response", "")
                else:
                    print(f"Ollama error: {response.status_code}")
                    return ""
            except Exception as e:
                print(f"Error calling Ollama: {e}")
                return ""

    llm = OllamaLLM()
    print("Starting AGI Cognitive Framework Benchmark...")
    score = agi_cognitive_framework_overall(llm)
    print(f"Final AGI Cognitive Framework Score: {score:.4f}")
