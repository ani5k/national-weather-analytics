import { useState } from 'react'
import { Check, X, Clock, ChevronDown, ChevronRight } from 'lucide-react'
import { updateReportStatus } from '../api/client'

const STATUS_STYLE = {
  verified: 'bg-verified/15 text-verified',
  pending: 'bg-warn/15 text-warn',
  rejected: 'bg-alert/15 text-alert',
}

function WhyScorePanel({ report }) {
  const factors = report.credibility_factors || []
  const reasons = report.credibility_reasons || []
  if (!factors.length && !reasons.length) {
    return <p className="text-[10px] text-text-muted mt-1">No factor breakdown yet — run enrichment.</p>
  }
  return (
    <div className="mt-2 rounded-md border border-storm/60 bg-void/80 p-2 space-y-1">
      <p className="text-[10px] font-mono text-text-muted uppercase tracking-wide">
        Why this score · {report.credibility_score}%
      </p>
      {factors.length > 0
        ? factors.map((f, idx) => {
            const delta = Number(f.delta) || 0
            const positive = delta >= 0
            return (
              <div key={`${f.factor}-${idx}`} className="flex justify-between gap-2 text-[10px]">
                <span className="text-text-primary">
                  {f.factor}
                  {f.detail ? ` · ${f.detail}` : ''}
                </span>
                <span className={`font-mono ${positive ? 'text-verified' : 'text-alert'}`}>
                  {positive ? '+' : ''}
                  {delta}
                </span>
              </div>
            )
          })
        : reasons.map((reason) => (
            <p key={reason} className="text-[10px] text-text-muted">
              {reason}
            </p>
          ))}
      {report.official_anchor_id && (
        <p className="text-[10px] text-rain font-mono mt-1">
          Anchored to IMD bulletin {report.official_anchor_id}
        </p>
      )}
      {report.media_forensics_detail && (
        <p className="text-[10px] text-alert mt-1">{report.media_forensics_detail}</p>
      )}
    </div>
  )
}

export default function AdminTable({ reports, onUpdate, modelStatus }) {
  const [openId, setOpenId] = useState(null)

  const handleAction = async (id, status) => {
    await updateReportStatus(id, status)
    onUpdate()
  }

  return (
    <div className="flex flex-col gap-3">
      {modelStatus && (
        <div className="rounded-md border border-thunder/40 bg-thunder/10 px-3 py-2 text-xs text-text-primary">
          <span className="font-medium">{modelStatus.message}</span>
          {modelStatus.last_refresh_at && (
            <span className="text-text-muted font-mono ml-2">
              refreshed {modelStatus.last_refresh_at}
            </span>
          )}
          {modelStatus.heldout_accuracy_after != null && (
            <span className="text-text-muted font-mono ml-2">
              held-out {modelStatus.heldout_accuracy_before ?? '—'} → {modelStatus.heldout_accuracy_after}
            </span>
          )}
        </div>
      )}

      <div className="bg-panel-raised border border-storm rounded-xl overflow-hidden shadow-glow">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-storm text-left text-text-muted text-xs uppercase tracking-wide">
              <th className="px-4 py-3">Report</th>
              <th className="px-4 py-3">Event</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Trust</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {reports.slice(0, 80).map((r) => {
              const open = openId === r.id
              return (
                <tr key={r.id} className="border-b border-storm/50 hover:bg-panel align-top">
                  <td className="px-4 py-3">
                    <p className="text-text-primary text-xs max-w-sm">{r.text}</p>
                    <p className="text-[10px] text-text-muted font-mono mt-1">
                      {r.id} · {r.source}
                    </p>
                    {!!r.hashtags?.length && (
                      <p className="text-[10px] text-rain mt-1">{r.hashtags.join(' ')}</p>
                    )}
                    <button
                      type="button"
                      className="mt-1 inline-flex items-center gap-1 text-[10px] text-rain hover:underline"
                      onClick={() => setOpenId(open ? null : r.id)}
                    >
                      {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      Why this score
                    </button>
                    {open && <WhyScorePanel report={r} />}
                  </td>
                  <td className="px-4 py-3 text-xs capitalize text-text-muted">
                    {r.event_type.replace('_', ' ')}
                    {r.risk_severity && (
                      <div className="text-[10px] font-mono mt-1">{r.risk_severity} risk</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-text-muted">
                    {r.city}, {r.state}
                  </td>
                  <td className="px-4 py-3">
                    <div className="w-16 h-1.5 bg-storm/40 rounded-full overflow-hidden">
                      <div className="h-full bg-rain" style={{ width: `${r.credibility_score}%` }} />
                    </div>
                    <span className="text-[10px] text-text-muted font-mono">{r.credibility_score}%</span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded ${STATUS_STYLE[r.verification_status]}`}
                      >
                        {r.verification_status}
                      </span>
                      <span
                        className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded border ${
                          r.verified_by === 'admin'
                            ? 'border-thunder/40 text-thunder'
                            : 'border-storm text-text-muted'
                        }`}
                      >
                        {r.verified_by === 'admin' ? 'Admin' : 'ML'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleAction(r.id, 'verified')}
                        className="p-1.5 rounded-md bg-verified/10 text-verified hover:bg-verified/20"
                        title="Verify"
                      >
                        <Check size={14} />
                      </button>
                      <button
                        onClick={() => handleAction(r.id, 'pending')}
                        className="p-1.5 rounded-md bg-warn/10 text-warn hover:bg-warn/20"
                        title="Mark pending"
                      >
                        <Clock size={14} />
                      </button>
                      <button
                        onClick={() => handleAction(r.id, 'rejected')}
                        className="p-1.5 rounded-md bg-alert/10 text-alert hover:bg-alert/20"
                        title="Reject"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
