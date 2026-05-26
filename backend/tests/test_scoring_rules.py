import unittest

from tests.test_questionnaire_bank_and_scoring import QuestionnaireBankAndScoringTests


class ScoringRulesSubsetTests(QuestionnaireBankAndScoringTests):
    def test_phq_like_total_range_alias(self):
        self.test_phq_like_builtin_uses_0_to_27_ranges()

    def test_gad_like_total_range_alias(self):
        self.test_gad_like_builtin_uses_0_to_21_ranges()

    def test_attention_not_in_total_alias(self):
        self.test_calculate_scores_uses_per_question_max_and_single_reverse()

    def test_reverse_only_once_alias(self):
        self.test_calculate_scores_uses_per_question_max_and_single_reverse()

    def test_dimension_pct_alias(self):
        self.test_dimension_percentages_use_dimension_max_score()

    def test_copy_contradiction_alias(self):
        self.test_copy_questionnaire_rewrites_contradiction_group_question_ids()

    def test_production_no_mingde_alias(self):
        self.test_production_env_never_seeds_school()


if __name__ == "__main__":
    unittest.main()
