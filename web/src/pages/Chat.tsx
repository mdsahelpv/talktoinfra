import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  tool_calls?: any[]
  requires_approval?: boolean
  approval_id?: string
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const sendMessage = async () => {
    if (!input.trim()) return
    const userMsg: Message = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.chat(input, sessionId)
      setSessionId(res.session_id)

      const assistantMsg: Message = {
        role: 'assistant',
        content: res.message,
        tool_calls: res.tool_calls || [],
        requires_approval: res.requires_approval,
        approval_id: res.approval_id || undefined,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${err}` }])
    }
    setLoading(false)
  }

  const handleApprove = async (approvalId: string) => {
    try {
      await api.approve(approvalId, true)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '✅ Approved and executed.' },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `❌ Approval failed: ${err}` },
      ])
    }
  }

  const handleDeny = async (approvalId: string) => {
    try {
      await api.approve(approvalId, false)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '❌ Action denied.' },
      ])
    } catch (err) {
      /* ignore */
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-2xl mb-2">🤖</p>
            <p className="text-lg">Ask me about your infrastructure</p>
            <p className="text-sm mt-2 text-gray-600">
              "Are there any failing pods?" · "What's the IP of the DNS server?"
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[70%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-cyan-700 text-white'
                  : 'bg-gray-800 text-gray-100'
              }`}
            >
              <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="mt-2 text-xs text-gray-400">
                  🔧 {msg.tool_calls.map((tc) => tc.action).join(', ')}
                </div>
              )}
              {msg.requires_approval && msg.approval_id && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleApprove(msg.approval_id!)}
                    className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded"
                  >
                    ✅ Approve
                  </button>
                  <button
                    onClick={() => handleDeny(msg.approval_id!)}
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded"
                  >
                    ❌ Deny
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-lg p-3 text-gray-400 text-sm">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-gray-800 p-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask about your infrastructure..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-cyan-500"
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-gray-700 text-white rounded-lg text-sm"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
