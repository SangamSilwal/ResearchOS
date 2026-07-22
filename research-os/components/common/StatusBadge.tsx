export interface StatusBadgeProps {
  status: 'queued' | 'running' | 'done' | 'error'
  className?: string
}

const statusStyles = {
  queued: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  done: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  error: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const statusLabels = {
  queued: 'Queued',
  running: 'Running',
  done: 'Completed',
  error: 'Error',
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${statusStyles[status]} ${className}`}
    >
      {status === 'running' && (
        <span className="inline-block w-2 h-2 rounded-full bg-current mr-2 animate-pulse" />
      )}
      {statusLabels[status]}
    </span>
  )
}
