// frontend/src/data/mockData.js

export const MOCK_JOBS = [
  {
    id: 1, status: 'DONE', n_samples: 3,
    papers_count: 3, claims_count: 12, conflicts_count: 4,
    started_at: '2026-06-13T10:00:00Z', finished_at: '2026-06-13T10:02:30Z',
    created_at: '2026-06-13T09:59:00Z',
  },
  {
    id: 2, status: 'RUNNING', n_samples: 1,
    papers_count: 2, claims_count: 5, conflicts_count: 0,
    started_at: '2026-06-13T14:00:00Z', finished_at: null,
    created_at: '2026-06-13T13:59:00Z',
  },
]

export const MOCK_PAPERS = [
  { id: 1, job_id: 1, title: 'Drug X efficacy in mouse tumor models',    claims_count: 6, created_at: '2026-06-13T10:01:00Z' },
  { id: 2, job_id: 1, title: 'Drug X Phase 2 clinical trial results',    claims_count: 6, created_at: '2026-06-13T10:01:30Z' },
  { id: 3, job_id: 1, title: 'Drug X mechanism of action study',         claims_count: 0, created_at: '2026-06-13T10:02:00Z' },
]

export const MOCK_CONFLICTS = [
  {
    id: 1, verdict: 'CONTRADICTS', conflict_type: 'direct', severity: 4,
    reasoning: 'Paper A reports 40% tumor reduction; Paper B finds no significant effect in clinical trials.',
    consistency_score: 1.0, final_confidence: 0.92,
    claim_a_id: 1, claim_b_id: 4,
    error_types: ['condition_dropping'],
    created_at: '2026-06-13T10:02:00Z',
  },
  {
    id: 2, verdict: 'PARTIAL', conflict_type: 'methodological', severity: 2,
    reasoning: 'Both papers study Drug X but use different dosage protocols and populations.',
    consistency_score: 0.67, final_confidence: 0.67,
    claim_a_id: 2, claim_b_id: 5,
    error_types: [],
    created_at: '2026-06-13T10:02:05Z',
  },
  {
    id: 3, verdict: 'SUPPORTS', conflict_type: 'none', severity: 1,
    reasoning: 'Both papers confirm the same mechanism of action for Drug X.',
    consistency_score: 1.0, final_confidence: 1.0,
    claim_a_id: 3, claim_b_id: 6,
    error_types: [],
    created_at: '2026-06-13T10:02:10Z',
  },
]

export const MOCK_MODELS = [
  'llama-3.3-70b-instruct',
  'medgemma-27b-it',
  'mistral-small-3.1',
  'gpt-oss-120b',
  'gemma-3-27b-it',
]
