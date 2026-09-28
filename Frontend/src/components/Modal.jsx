import { X } from 'lucide-react'
import { useEffect } from 'react'

export default function Modal({ title, subtitle, onClose, children, wide = false }) {
  // Close on Escape — small touch, but expected behavior that's easy to forget
  useEffect(() => {
    const handler = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-text-primary/30 backdrop-blur-[2px] p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`bg-void border border-storm rounded-lg shadow-glow w-full ${
          wide ? 'max-w-3xl' : 'max-w-lg'
        } max-h-[85vh] overflow-y-auto`}
      >
        <div className="flex items-start justify-between px-5 py-4 border-b border-storm sticky top-0 bg-void">
          <div>
            <h2 className="font-display font-semibold text-lg text-text-primary">{title}</h2>
            {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary p-1 rounded-md hover:bg-panel"
          >
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}
