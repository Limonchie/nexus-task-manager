import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Task, type TaskListResponse } from "../../api/client";

export function TaskListPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", page, status || undefined],
    queryFn: () =>
      api.get<TaskListResponse>(
        "/tasks",
        Object.assign(
          { page: String(page), size: "20" },
          status ? { status } : {}
        )
      ),
  });

  const createMutation = useMutation({
    mutationFn: (body: { title: string; description?: string }) =>
      api.post<Task>("/tasks", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<Task> }) =>
      api.patch<Task>(`/tasks/${id}`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/tasks/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    createMutation.mutate(
      { title: title.trim(), description: description.trim() || undefined },
      {
        onSuccess: () => {
          setTitle("");
          setDescription("");
        },
      }
    );
  };

  if (isLoading || !data) return <div className="p-4">Loading tasks...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Tasks</h2>

      <form onSubmit={handleCreate} className="flex gap-2 mb-6">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New task title"
          className="flex-1 border border-gray-300 rounded px-3 py-2"
        />
        <input
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description (optional)"
          className="flex-1 border border-gray-300 rounded px-3 py-2"
        />
        <button
          type="submit"
          disabled={createMutation.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          Add
        </button>
      </form>

      <div className="flex gap-2 mb-4">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2"
        >
          <option value="">All statuses</option>
          <option value="todo">Todo</option>
          <option value="in_progress">In progress</option>
          <option value="done">Done</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <ul className="space-y-2">
        {data.items.map((task) => (
          <li
            key={task.id}
            className="bg-white border rounded-lg p-4 flex items-center justify-between"
          >
            <div>
              <p className="font-medium">{task.title}</p>
              {task.description && (
                <p className="text-sm text-gray-600">{task.description}</p>
              )}
              <span className="text-xs text-gray-500">{task.status}</span>
            </div>
            <div className="flex items-center gap-2">
              <select
                value={task.status}
                onChange={(e) =>
                  updateMutation.mutate({
                    id: task.id,
                    body: { status: e.target.value as Task["status"] },
                  })
                }
                className="border rounded px-2 py-1 text-sm"
              >
                <option value="todo">Todo</option>
                <option value="in_progress">In progress</option>
                <option value="done">Done</option>
                <option value="cancelled">Cancelled</option>
              </select>
              <button
                onClick={() => deleteMutation.mutate(task.id)}
                className="text-red-600 text-sm hover:underline"
              >
                Delete
              </button>
            </div>
          </li>
        ))}
      </ul>

      {data.pages > 1 && (
        <div className="mt-4 flex gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="py-1">
            Page {page} of {data.pages}
          </span>
          <button
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
