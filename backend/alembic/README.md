# Alembic 迁移链

当前迁移链为线性单 head：

```
<base>
  ↓
202605260001 — initial phase 1 baseline（Base.metadata.create_all）
  ↓
202605260002 — phase 2 core fields and external logs（tasks/answer_sheets/risk_alerts/interventions 补充字段、sms_logs/ai_analysis_logs 新增表）
  ↓
202605260003_questionnaire_rule_fields — questionnaire rule fields（questionnaires 的 code/source_type/disclaimer/dimensions/scoring_rule/risk_rules/quality_rules/builtin_content_hash、questions 的 code、answer_records 的 selected_display_index、code 非空唯一索引）
  ↓
202605260003 — questionnaire rule bank fields（历史兼容迁移，字段与 202605260003_questionnaire_rule_fields 部分重复，通过 _add_column_if_missing 保持幂等）
  ↓
202605260004 — missing questionnaire columns（questions.risk_threshold、options.is_risk_option、answer_sheets.ip_address/user_agent）
  ↑ head
```

## 规则

1. 后续新迁移必须从 `202605260004` 继续追加，revision 使用新的时间戳前缀。
2. 不要再新增 `202605260003` 前缀的迁移。
3. 每次新增迁移时使用 `_add_column_if_missing` 确保幂等。
4. 使用 `alembic revision -m "description"` 生成新迁移文件，手动填写 `down_revision`。
