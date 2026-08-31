export type Member = {
  member_id: string; name: string; first_name: string; last_name: string; age_band: string;
  preferred_language: string; preferred_contact_channel: string; plan_id: string; plan_name: string;
  plan_type: string; coverage_status: string; zip3: string; county: string; communication_consent: boolean;
  last_advocate_call: string | null; last_call_topic: string | null; last_call_follow_up_required: boolean;
  claims_90d: number; claims_180d: number; calls_90d: number; authorization_count_180d: number;
  latest_activity_date: string | null; claim_count: number;
}

export type EvidenceItem = { type: string; description: string; source_id?: string | null; date?: string | null }
export type CareIntent = {
  member_id: string;
  care_intent: { detected: boolean; predicted_care_event: string | null; care_category: string | null; confidence: number; confidence_band?: 'HIGH'|'MODERATE_HIGH'|'MODERATE'|'LOW'|'MINIMAL'; confidence_band_reason?: string; estimated_time_window: string | null };
  advocate_contact: { risk_level: 'LOW'|'MEDIUM'|'HIGH'; confidence: number; reason: string };
  evidence: EvidenceItem[];
  recommended_action: 'RUN_READINESS_ASSESSMENT'|'MONITOR';
  threshold: number; transcript_tool_invoked: boolean; generated_by: string; prompt_version?: string;
}
export type ReadinessItem = { key:string; label:string; status:'READY'|'NEEDS_ATTENTION'|'IN_PROGRESS'|'UNKNOWN'|'NOT_APPLICABLE'; detail:string; deduction:number }
export type Alternative = { provider_id:string; provider_name:string; organization_name:string; specialty:string; city:string; state:string; zip3:string; network_status:string; accepting_new_patients:boolean }
export type Readiness = { member_id:string; predicted_care_event:string; readiness_score:number; readiness_label:string; checklist:ReadinessItem[]; top_issue:string|null; score_explanation:string[]; alternatives:Alternative[]; recommended_next_action:string; generated_by:string; weight_rationale?:string; provider_provenance?:string[] }
export type QueueRow = { member_id:string; predicted_care_event:string; care_intent_confidence:number; estimated_time_window:string|null; advocate_contact_risk:string; advocate_contact_confidence:number; readiness:number|null; top_issue:string; status:string }
export type CallRecord = { call_id:string; timestamp:string; duration_seconds:number; topic:string; disposition:string; summary:string|null; member_need:string|null; advocate_action:string|null; follow_up_required:boolean; follow_up_note:string|null; transcript_available:boolean }
export type Claim = { claim_id:string; service_date:string; diagnosis_code:string; diagnosis_description:string; procedure_code:string; procedure_description:string; provider_id:string; facility_id:string; allowed_amount:number; member_responsibility:number; network_status_at_service:string }

export type LandingSummary = {
  members:number; claims_180d:number; calls_90d:number; authorizations:number; prompt_tokens_used:number;
  prompt_tokens_label?:string; has_usage?:boolean;
  openai_configured:boolean; model:string; data_as_of:string;
}
export type HealthStatus = { status:string; service:string; openai_configured:boolean; model:string; data_as_of:string; mock_ai:boolean; temperature?:number; prompt_version?:string; scan_concurrency?:number; max_scan_batch?:number }

export type MemberPage = { members:Member[]; total:number; offset:number; limit:number; has_more:boolean; candidates_only:boolean }

export type EvalLabels = {
  total:number; by_label:Record<string,number>; index_date:string; method:string; limitation:string;
  examples:{member_id:string;label:string;actual_procedure:string;actual_service_date:string;days_from_index:number}[];
}
export type ScoreBlock = {
  threshold:number; scored_members:number; excluded_ambiguous:number;
  true_positives:number; false_positives:number; false_negatives:number; true_negatives:number;
  precision:number; recall:number; f1:number; procedure_named_correctly:number; procedure_accuracy:number;
  misses:{member_id:string;actual:string;confidence:number;days_out:number}[];
  false_alarms:{member_id:string;predicted:string;confidence:number}[];
  interpretation:string;
}
export type BacktestResult = {
  run_id:string; index_date:string; model:string; prompt_version:string;
  members_assessed:number; failed:number; scored:ScoreBlock;
  threshold_sweep:{threshold:number;precision:number;recall:number;f1:number;true_positives:number;false_positives:number;false_negatives:number}[];
  mean_groundedness:number; groundedness_note:string;
}
export type PerturbationResult = {
  member_id:string;
  cases:{case:string;confidence:number;predicted_care_event:string|null;description:string}[];
  verdict:{baseline_confidence:number;stripped_confidence:number;contradicted_confidence:number;drop_when_evidence_removed:number;drop_when_contradicted:number;passed:boolean;interpretation:string};
}
export type DecisionStats = {
  total_decisions:number; approved:number; saved:number; rejected:number; edited:number;
  approval_rate:number; edit_rate:number;
  by_message_class:{key:string;total:number;approved:number;edited:number;rejected:number;approval_rate:number;edit_rate:number}[];
  by_top_issue:{key:string;total:number;approved:number;edited:number;rejected:number;approval_rate:number;edit_rate:number}[];
  note:string;
}
export type CareBatchRow = { member: Member; assessment: CareIntent }
export type CareBatchResult = { selected_count:number; model:string; threshold:number; concurrency?:number; failed_count?:number; results:CareBatchRow[] }
export type ReadinessBatchRow = { member:Member; care_intent:CareIntent; readiness:Readiness }
export type ReadinessBatchResult = { selected_count:number; processed_count:number; model:string; results:ReadinessBatchRow[]; skipped:{member_id:string;reason:string}[] }

export type ChecklistLine = {
  key:string; label:string; status:string; member_status:string; detail:string; is_top_issue:boolean
}

/** The member notification: the full readiness checklist with one highlighted action. */
export type OutreachDraft = {
  member_id:string; channel:string; message:string; human_approval_required:boolean;
  message_class?:string; gating_policy?:string; top_issue?:string|null;
  headline?:string; predicted_care_event?:string; readiness_score?:number; readiness_label?:string;
  highlighted_action?:string; checklist?:ChecklistLine[]; ready_count?:number; total_items?:number;
  resolution_mode?:'CHOOSE_OPTION'|'CONFIRM'|'NO_ACTION'|'ADVOCATE';
  call_to_action?:string; member_options?:MemberOption[];
  advocate_required?:boolean; advocate_reason?:string; alternatives?:Alternative[];
}
export type MemberOption = { option_id:string; label:string; sublabel:string; kind:string }
