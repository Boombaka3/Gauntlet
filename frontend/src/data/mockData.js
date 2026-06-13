// frontend/src/data/mockData.js

export const MOCK_SUITES = [
  {
    id: 1,
    name: 'Summarization Benchmark',
    version: 1,
    description: 'Tests model summarization quality',
    rubric: { accuracy: 0.6, conciseness: 0.4 },
    baseline_run_id: null,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-06-01T10:00:00Z',
  },
  {
    id: 2,
    name: 'Code Generation Suite',
    version: 2,
    description: 'Evaluates code correctness and style',
    rubric: { correctness: 0.7, readability: 0.3 },
    baseline_run_id: null,
    created_at: '2026-06-02T14:00:00Z',
    updated_at: '2026-06-02T14:00:00Z',
  },
]

export const MOCK_CASES = [
  {
    id: 1,
    suite_id: 1,
    name: 'Short article summary',
    system_prompt: 'You are a summarization assistant.',
    user_prompt: 'Summarize in one sentence: The quick brown fox jumps over the lazy dog.',
    expected_output: 'A fox jumps over a dog.',
    tags: [],
    created_at: '2026-06-01T10:05:00Z',
  },
  {
    id: 2,
    suite_id: 1,
    name: 'Technical summary',
    system_prompt: 'You are a technical writer.',
    user_prompt: 'Summarize the concept of database indexing in one sentence.',
    expected_output: 'Database indexing speeds up queries by creating sorted references to rows.',
    tags: ['technical'],
    created_at: '2026-06-01T10:10:00Z',
  },
]

export const MOCK_RUNS = [
  {
    id: 1,
    suite_id: 1,
    status: 'DONE',
    score_mode: 'rubric',
    model_ids: ['claude-haiku-4-5-20251001', 'gpt-4o'],
    progress: 4,
    total: 4,
    baseline_run_id: null,
    started_at: '2026-06-07T10:00:00Z',
    finished_at: '2026-06-07T10:00:45Z',
    result_s3_key: null,
    created_at: '2026-06-07T10:00:00Z',
  },
]

export const MOCK_RESULTS = [
  {
    id: 1,
    model_run_id: 1,
    model_id: 'claude-haiku-4-5-20251001',
    prompt_case_id: 1,
    overall: 0.87,
    passed: true,
    scores: { accuracy: 4, conciseness: 4 },
    judge_reasoning: 'Accurate and appropriately concise.',
    regression_delta: null,
    latency_ms: 342,
    created_at: '2026-06-07T10:00:10Z',
  },
  {
    id: 2,
    model_run_id: 2,
    model_id: 'gpt-4o',
    prompt_case_id: 1,
    overall: 0.74,
    passed: true,
    scores: { accuracy: 4, conciseness: 3 },
    judge_reasoning: 'Accurate but slightly verbose.',
    regression_delta: -0.05,
    latency_ms: 891,
    created_at: '2026-06-07T10:00:12Z',
  },
  {
    id: 3,
    model_run_id: 3,
    model_id: 'gemini-1.5-flash',
    prompt_case_id: 2,
    overall: 0.61,
    passed: false,
    scores: { accuracy: 3, conciseness: 3 },
    judge_reasoning: 'Acceptable but missed key details.',
    regression_delta: null,
    latency_ms: 1240,
    created_at: '2026-06-07T10:00:15Z',
  },
]

export const MOCK_MODELS = [
  'claude-haiku-4-5-20251001',
  'claude-sonnet-4-6',
  'gpt-4o',
  'gpt-4o-mini',
  'gemini-1.5-pro',
  'gemini-1.5-flash',
]
