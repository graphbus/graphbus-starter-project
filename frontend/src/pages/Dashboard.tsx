import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getMe, getTasks, type TaskItem, type UserProfile } from "../api/client";
import TaskForm from "../components/TaskForm";
import TaskList from "../components/TaskList";

export default function Dashboard() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [me, taskList] = await Promise.all([getMe(), getTasks()]);
      setUser(me);
      setTasks(taskList);
    } catch {
      localStorage.removeItem("token");
      navigate("/");
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function handleLogout() {
    localStorage.removeItem("token");
    navigate("/");
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-8">
      {/* header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-500">
            Welcome, {user?.name ?? "User"}
          </p>
        </div>
        <button
          onClick={handleLogout}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100"
        >
          Sign out
        </button>
      </div>

      {/* add task */}
      <div className="mt-8">
        <TaskForm onCreated={fetchData} />
      </div>

      {/* task list */}
      <div className="mt-6">
        <TaskList tasks={tasks} onChanged={fetchData} />
      </div>
    </div>
  );
}
