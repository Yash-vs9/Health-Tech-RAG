import Sidebar from "../components/Sidebar";
import Chatbox from "../components/Chatbox";

export default function Dashboard() {
  return (
    <div className="dashboard">
      <Sidebar />
      <Chatbox />
    </div>
  );
}