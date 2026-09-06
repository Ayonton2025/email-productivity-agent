import { useSyncExternalStore } from 'react'
import { notifications } from '../../utils/notifications'
export default function ToastProvider({ children }) {
  const items = useSyncExternalStore(notifications.subscribe, notifications.getSnapshot)
  return (
    <>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex max-w-sm flex-col gap-2" aria-label="Notifications">
        {items.map((item) => (
          <div
            key={item.id}
            role={item.type === 'error' ? 'alert' : 'status'}
            className="rounded-lg border border-slate-300 bg-white p-4 text-slate-900 shadow-lg"
          >
            <p>{item.message}</p>
            <button
              type="button"
              onClick={() => notifications.dismiss(item.id)}
              aria-label="Dismiss notification"
              className="mt-2 text-sm underline"
            >
              Dismiss
            </button>
          </div>
        ))}
      </div>
    </>
  )
}
