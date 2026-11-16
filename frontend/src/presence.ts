import { useEffect, useState } from "react";

export function usePresence(projectId: string): string[] {
  const [users, setUsers] = useState<string[]>([]);
  useEffect(() => {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(
      `${scheme}://${window.location.host}/api/ws/projects/${projectId}`
    );
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "presence") setUsers(message.users);
      } catch {
        // non-JSON frames are ignored
      }
    };
    const heartbeat = window.setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) socket.send("ping");
    }, 25000);
    return () => {
      window.clearInterval(heartbeat);
      socket.close();
      setUsers([]);
    };
  }, [projectId]);
  return users;
}
