import { useState } from 'react'
import { CITIES, EVENT_TYPE_META } from '../api/mockData'
import { createCitizenReport } from '../api/client'

export default function CitizenReportForm({ onCreated }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [city, setCity] = useState('Mumbai')
  const [eventType, setEventType] = useState('')
  const [mediaUrl, setMediaUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setMsg('')
    try {
      await createCitizenReport({
        text,
        city,
        event_type: eventType || undefined,
        media_url: mediaUrl || undefined,
      })
      setText('')
      setMediaUrl('')
      setMsg('Report submitted')
      onCreated?.()
      setOpen(false)
    } catch (err) {
      setMsg(err?.message || 'Submit failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs px-3 py-1.5 rounded-md border border-rain text-rain hover:bg-rain/10"
      >
        {open ? 'Close form' : 'Submit citizen report'}
      </button>
      {open && (
        <form onSubmit={submit} className="mt-3 border border-storm rounded-lg p-3 bg-panel flex flex-col gap-2 max-w-xl">
          <textarea
            required
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Describe the weather event… include #IMD if relevant"
            className="bg-void border border-storm rounded-md px-2 py-1.5 text-sm min-h-[80px]"
          />
          <div className="flex flex-wrap gap-2">
            <select
              value={city}
              onChange={(e) => setCity(e.target.value)}
              className="bg-void border border-storm rounded-md px-2 py-1.5 text-sm"
            >
              {CITIES.map((c) => (
                <option key={c.city} value={c.city}>
                  {c.city}
                </option>
              ))}
            </select>
            <select
              value={eventType}
              onChange={(e) => setEventType(e.target.value)}
              className="bg-void border border-storm rounded-md px-2 py-1.5 text-sm"
            >
              <option value="">Auto-detect event</option>
              {EVENT_TYPE_META.map((et) => (
                <option key={et.key} value={et.key}>
                  {et.label}
                </option>
              ))}
            </select>
          </div>
          <input
            value={mediaUrl}
            onChange={(e) => setMediaUrl(e.target.value)}
            placeholder="Optional media URL"
            className="bg-void border border-storm rounded-md px-2 py-1.5 text-sm"
          />
          <button
            disabled={busy}
            type="submit"
            className="self-start px-3 py-1.5 rounded-md bg-rain text-white text-sm disabled:opacity-50"
          >
            {busy ? 'Sending…' : 'Submit'}
          </button>
          {msg && <p className="text-xs text-text-muted">{msg}</p>}
        </form>
      )}
    </div>
  )
}
