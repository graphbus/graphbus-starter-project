import { useState } from "react";
import { deleteTask, updateTask, type TaskItem } from "../api/client";

interface TaskListProps {
  tasks: TaskItem[];
  onChanged: () => void;
}

export default function TaskList({ tasks, onChanged }: TaskListProps) {
  const [busyId, setBusyId] = useState<string | null>(null);

  async function handleToggle(task: TaskItem) {
    setBusyId(task.id);
    try {
      await updateTask(task.id, { done: !task.done });
      onChanged();
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(id: string) {
    setBusyId(id);
    try {
      await deleteTask(id);
      onChanged();
    } finally {
      setBusyId(null);
    }
  }

  if (tasks.length === 0) {
    return (
      <p className="text-center text-sm text-gray-400">
        No tasks yet. Add one above!
      </p>
    );
  }

  return (
    <ul className="divide-y divide-gray-200 rounded border border-gray-200">
      {tasks.map((task) => (
        <li
          key={task.id}
          className="flex items-center gap-3 px-4 py-3"
        >
          <input
            type="checkbox"
            checked={task.done}
            disabled={busyId === task.id}
            onChange={() => handleToggle(task)}
            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span
            className={`flex-1 text-sm ${task.done ? "text-gray-400 line-through" : ""}`}
          >
            {task.title}
          </span>
          <button
            onClick={() => handleDelete(task.id)}
            disabled={busyId === task.id}
            className="text-sm text-red-500 hover:text-red-700 disabled:opacity-50"
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}
