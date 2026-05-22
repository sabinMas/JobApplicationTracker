import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd'
import { Job } from '../api/client'
import { ApplicationCard } from './ApplicationCard'
import { useUpdateJob } from '../hooks/useJobs'

const COLUMNS: { id: string; label: string }[] = [
  { id: 'discovered', label: '🔍 Discovered' },
  { id: 'saved',      label: '⭐ Saved' },
  { id: 'applying',   label: '✍️ Applying' },
  { id: 'applied',    label: '📤 Applied' },
  { id: 'dropped',    label: '❌ Dropped' },
]

interface Props {
  jobs: Job[]
}

export function KanbanBoard({ jobs }: Props) {
  const updateJob = useUpdateJob()

  const onDragEnd = (result: DropResult) => {
    if (!result.destination) return
    const jobId = parseInt(result.draggableId)
    const newStatus = result.destination.droppableId
    updateJob.mutate({ id: jobId, data: { status: newStatus } })
  }

  const grouped = COLUMNS.reduce<Record<string, Job[]>>((acc, col) => {
    acc[col.id] = jobs.filter(j => j.status === col.id)
    return acc
  }, {})

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="flex gap-4 overflow-x-auto pb-4 h-full">
        {COLUMNS.map(col => (
          <div key={col.id} className="flex-shrink-0 w-64">
            {/* Column header */}
            <div className="flex items-center justify-between mb-3 px-1">
              <span className="font-semibold text-sm text-gray-700">{col.label}</span>
              <span className="text-xs bg-parchment-200 text-gray-600 rounded-full px-2 py-0.5">
                {grouped[col.id].length}
              </span>
            </div>

            {/* Droppable column */}
            <Droppable droppableId={col.id}>
              {(provided, snapshot) => (
                <div
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                  className={`min-h-[200px] rounded-xl p-2 transition-colors ${
                    snapshot.isDraggingOver ? 'bg-emerald-50' : 'bg-parchment-100'
                  }`}
                >
                  <div className="flex flex-col gap-2">
                    {grouped[col.id].map((job, idx) => (
                      <Draggable key={job.id} draggableId={String(job.id)} index={idx}>
                        {(prov, snap) => (
                          <div
                            ref={prov.innerRef}
                            {...prov.draggableProps}
                            {...prov.dragHandleProps}
                          >
                            <ApplicationCard job={job} dragging={snap.isDragging} />
                          </div>
                        )}
                      </Draggable>
                    ))}
                  </div>
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </div>
        ))}
      </div>
    </DragDropContext>
  )
}
