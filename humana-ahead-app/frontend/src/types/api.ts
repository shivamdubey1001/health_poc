export type Member = {
  member_id: string; name: string; first_name: string; last_name: string; age_band: string;
  preferred_language: string; preferred_contact_channel: string; plan_id: string; plan_name: string;
  plan_type: string; coverage_status: string; zip3: string; county: string; communication_consent: boolean;
  last_advocate_call: string | null; claim_count: number;
}

export type EvidenceItem = { type: string; description: string; source_id?: string | null; date?: string | null }
export type CareIntent = {
  member_id: string;
  care_intent: { detected: boolean; predicted_care_event: string | null; care_category: string | null; confidence: number; estimated_time_window: string | null };
  advocate_contact: { risk_level: 'LOW'|'MEDIUM'|'HIGH'; confidence: number; reason: string };
  evidence: EvidenceItem[];
  recommended_action: 'RUN_READINESS_ASSESSMENT'|'MONITOR';
  threshold: number; transcript_tool_invoked: boolean; generated_by: string;
}
export type ReadinessItem = { key:string; label:string; status:'READY'|'NEEDS_ATTENTION'|'IN_PROGRESS'|'UNKNOWN'|'NOT_APPLICABLE'; detail:string; deduction:number }
export type Alternative = { provider_id:string; provider_name:string; organization_name:string; specialty:string; city:string; state:string; zip3:string; network_status:string; accepting_new_patients:boolean }
export type Readiness = { member_id:string; predicted_care_event:string; readiness_score:number; readiness_label:string; checklist:ReadinessItem[]; top_issue:string|null; score_explanation:string[]; alternatives:Alternative[]; recommended_next_action:string }
export type QueueRow = { member_id:string; member_name:string; plan_name:string; predicted_care_event:string; care_intent_confidence:number; estimated_time_window:string|null; advocate_contact_risk:string; advocate_contact_confidence:number; readiness:number|null; top_issue:string; status:string }
export type CallRecord = { call_id:string; timestamp:string; duration_seconds:number; topic:string; disposition:string; summary:string|null; member_need:string|null; advocate_action:string|null; follow_up_required:boolean; follow_up_note:string|null; transcript_available:boolean }
export type Claim = { claim_id:string; service_date:string; diagnosis_code:string; diagnosis_description:string; procedure_code:string; procedure_description:string; provider_id:string; facility_id:string; allowed_amount:number; member_responsibility:number; network_status_at_service:string }
