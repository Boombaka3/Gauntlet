// frontend/src/pages/Chat.jsx
import { useState, useRef, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { getJob, chatWithJob } from '../api/client.js'

const SUGGESTED = [
  "What does the evidence say about this topic?",
  "Which papers show the strongest evidence?",
  "What are the key findings across papers?",
  "Where do the papers agree or disagree?",
  "What confidence scores were assigned to the answers?",
]

export default function Chat() {
  const { id } = useParams()
  const [messages, setMessages] = useState([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef = useRef(null)

  const { data: job } = useApi(() => getJob(id), null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(question) {
    const q = (question ?? input).trim()
    if (!q || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const res = await chatWithJob(id, q)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        sources: res.sources || [],
        model: res.model,
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err.message}`,
        sources: [],
        error: true,
      }])
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-48px)]">

      {/* Header */}
      <div className="border-b border-[#23252a] px-6 py-3 flex items-center gap-3 flex-shrink-0">
        <Link
          to={`/jobs/${id}/status`}
          className="text-[#62666d] hover:text-[#5e6ad2] text-xs font-mono transition-colors"
        >
          ← Job #{id}
        </Link>
        <span className="text-[#23252a]">|</span>
        <span className="text-[#f7f8f8] text-sm font-medium">
          {job?.title || `Analysis #${id}`}
        </span>
        <span className="ml-auto text-[#62666d] text-[10px] font-mono">
          {job?.answer_count || 0} answers in context
        </span>
      </div>

      {/* Message area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

        {/* Empty state with suggestions */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <div className="text-center">
              <p className="text-[#f7f8f8] text-sm font-medium mb-1">
                Ask about the evidence
              </p>
              <p className="text-[#8a8f98] text-xs">
                Questions are answered using stored QA results and extracted claims.
              </p>
            </div>
            <div className="flex flex-col gap-2 w-full max-w-md">
              {SUGGESTED.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(s)}
                  className="text-left px-4 py-2.5 bg-[#0f1011] border border-[#23252a]
                             hover:border-[#5e6ad2] rounded-[8px] text-[#d0d6e0] text-xs
                             transition-colors font-mono"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message bubbles */}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-2xl ${msg.role === 'user' ? 'ml-12' : 'mr-12'}`}>

              {/* Bubble */}
              <div className={`px-4 py-3 rounded-[12px] text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#5e6ad2] text-white'
                  : msg.error
                    ? 'bg-[#0f1011] border border-[#EF4444]/30 text-[#EF4444]'
                    : 'bg-[#0f1011] border border-[#23252a] text-[#d0d6e0]'
              }`}>
                {msg.content}
              </div>

              {/* Source citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.sources.map((src, j) => (
                    <div
                      key={j}
                      className="px-3 py-2 bg-[#141516] border border-[#23252a]
                                 rounded-[8px] text-[10px] font-mono"
                    >
                      <span className={`mr-2 font-semibold ${
                        src.answer === 'yes'   ? 'text-[#27a644]' :
                        src.answer === 'no'    ? 'text-[#EF4444]' :
                                                 'text-[#F59E0B]'
                      }`}>
                        {src.answer?.toUpperCase()}
                      </span>
                      <span className="text-[#8a8f98]">
                        {(src.paper || '').slice(0, 60)}
                      </span>
                      {src.confidence != null && (
                        <span className="text-[#62666d] ml-2">
                          conf={src.confidence.toFixed(2)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Model tag */}
              {msg.role === 'assistant' && msg.model && !msg.error && (
                <p className="text-[#62666d] text-[10px] font-mono mt-1 px-1">
                  {msg.model}
                </p>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#0f1011] border border-[#23252a] rounded-[12px]
                            px-4 py-3 text-sm text-[#8a8f98]">
              <span className="animate-pulse">Searching evidence…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-[#23252a] px-6 py-4 flex-shrink-0">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask a question about the evidence…"
            disabled={loading}
            className="flex-1 bg-[#0f1011] border border-[#23252a] rounded-[8px]
                       px-4 py-2.5 text-[#f7f8f8] text-sm placeholder-[#62666d]
                       focus:outline-none focus:border-[#5e6ad2] transition-colors
                       disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="px-4 py-2.5 bg-[#5e6ad2] hover:bg-[#828fff] disabled:opacity-40
                       text-white text-sm font-medium rounded-[8px] transition-colors
                       whitespace-nowrap"
          >
            Send
          </button>
        </div>
        <p className="text-[#62666d] text-[10px] font-mono text-center mt-2">
          Answers drawn from {job?.answer_count || 0} stored QA results across {job?.paper_count || 0} papers
        </p>
      </div>
    </div>
  )
}
